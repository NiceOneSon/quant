"""유니버스 수집(ingest). 소스에서 멤버십을 받아 정규화 후 reference parquet 으로 저장한다.

부수효과(파일 쓰기)는 여기로 격리한다. 정규화/검증은 순수 함수(normalize_memberships)로
분리해 테스트한다.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from common.logging import get_logger
from data_layer.loader import PRICE_SCHEMA, prices_path
from data_layer.rates import RATE_SCHEMA, RATE_SERIES, rates_path, series_country
from data_layer.sources import PriceSource, RateSource, UniverseSource
from data_layer.universe import (
    Membership,
    memberships_to_frame,
    universe_path,
)
from data_layer.universe_snapshots import rebuild_universe, record_snapshot

log = get_logger(__name__)


def normalize_memberships(memberships: list[Membership]) -> list[Membership]:
    """멤버십을 검증·정렬한다 (순수). 수동 주입(CSV) 데이터의 무결성을 지키는 관문.

    - 편출일이 편입일보다 앞서면 데이터 오류 → 거부.
    - 같은 종목의 멤버십 구간 [added, removed) 이 서로 겹치면 데이터 오류 → 거부.
      (갭이 있는 재편입은 허용: 예) 2010~2015 편출 후 2018 재편입.)
    - (symbol, added) 기준 정렬로 결정적 저장 보장(재현성).

    Raises:
        ValueError: removed < added 이거나, 동일 종목 구간이 겹치는 경우.
    """
    for m in memberships:
        if m.removed is not None and m.removed < m.added:
            raise ValueError(
                f"편출일이 편입일보다 앞섭니다: {m.symbol} added={m.added} removed={m.removed}"
            )

    ordered = sorted(memberships, key=lambda m: (m.symbol, m.added))
    for prev, cur in zip(ordered, ordered[1:], strict=False):
        if prev.symbol != cur.symbol:
            continue
        prev_end = prev.removed if prev.removed is not None else date.max
        if cur.added < prev_end:
            raise ValueError(
                f"멤버십 구간이 겹칩니다: {cur.symbol} "
                f"[{prev.added}, {prev.removed}) 와 [{cur.added}, {cur.removed})"
            )
    return ordered


def ingest_universe(
    source: UniverseSource,
    name: str,
    *,
    data_dir: Path | None = None,
) -> Path:
    """소스에서 `name` 유니버스를 수집해 point-in-time parquet 으로 저장한다.

    Returns:
        저장된 parquet 경로.
    """
    memberships = normalize_memberships(source.fetch(name))
    path = universe_path(name, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = memberships_to_frame(memberships).with_columns(pl.lit(name).alias("universe"))
    frame.write_parquet(path)
    log.info("universe ingested | name=%s rows=%d -> %s", name, len(memberships), path)
    return path


def ingest_universe_snapshot(
    source: UniverseSource,
    name: str,
    asof: date,
    *,
    data_dir: Path | None = None,
) -> Path:
    """현재 상장목록 스냅샷을 누적하고 멤버십 구간을 재구성한다(스냅샷 소스용, 예: FDR).

    소스의 현재 멤버를 (asof) 스냅샷으로 로그에 더한 뒤 누적분으로 universe 를 재빌드한다.
    주기적으로 실행할수록 편출·상폐가 반영돼 생존편향이 줄어든다.
    """
    symbols = [m.symbol for m in source.fetch(name)]
    n_snaps = record_snapshot(name, asof, symbols, data_dir=data_dir)
    n_members = rebuild_universe(name, data_dir=data_dir)
    path = universe_path(name, data_dir)
    log.info(
        "universe snapshot accumulated | name=%s asof=%s symbols=%d snapshots=%d members=%d -> %s",
        name,
        asof,
        len(symbols),
        n_snaps,
        n_members,
        path,
    )
    return path


def normalize_prices(frame: pl.DataFrame) -> pl.DataFrame:
    """가격 프레임을 저장 스키마로 정규화한다 (순수).

    - is_halted = 거래량 0 (거래정지/무거래). 백테스트가 체결 가능으로 오인하지 않도록 표시.
    - PRICE_SCHEMA 컬럼 순서·타입으로 맞추고 (symbol, date) 정렬(재현성).
    """
    return (
        frame.with_columns((pl.col("volume") == 0).alias("is_halted"))
        .select(list(PRICE_SCHEMA))
        .cast(PRICE_SCHEMA)  # type: ignore[arg-type]
        .sort(["symbol", "date"])
    )


def ingest_prices(
    source: PriceSource,
    universe: str,
    tickers: list[str],
    start: date,
    end: date,
    *,
    data_dir: Path | None = None,
) -> Path:
    """`tickers` 각각의 OHLCV 를 수집해 `universe` 가격 parquet 으로 저장한다.

    tickers 는 해당 유니버스에 한 번이라도 편입됐던 모든 종목이어야 한다(상장폐지 포함 →
    생존편향 방지). 빈 응답(데이터 없음) 종목은 건너뛴다.
    """
    frames: list[pl.DataFrame] = []
    for ticker in tickers:
        bars = source.fetch(ticker, start, end)
        if bars.height == 0:
            log.warning("no price data | ticker=%s", ticker)
            continue
        frames.append(bars.with_columns(pl.lit(ticker).alias("symbol")))

    if frames:
        combined = pl.concat(frames).with_columns(pl.lit(universe).alias("universe"))
        out = normalize_prices(combined)
    else:
        out = pl.DataFrame(schema=PRICE_SCHEMA)

    path = prices_path(universe, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.write_parquet(path)
    log.info(
        "prices ingested | universe=%s tickers=%d rows=%d -> %s",
        universe,
        len(frames),
        out.height,
        path,
    )
    return path


def ingest_rates(
    source: RateSource,
    series: str,
    start: date,
    end: date,
    *,
    data_dir: Path | None = None,
) -> Path:
    """금리 시리즈를 수집해 reference parquet 으로 저장한다 (date, series, country, rate)."""
    if series not in RATE_SERIES:
        log.warning("미등록 금리 시리즈 series=%s → country=NA", series)
    frame = source.fetch(start, end)  # date, rate
    out = (
        frame.with_columns(
            pl.lit(series).alias("series"),
            pl.lit(series_country(series)).alias("country"),
        )
        .select(list(RATE_SCHEMA))
        .cast(RATE_SCHEMA)  # type: ignore[arg-type]
        .sort("date")
    )
    path = rates_path(series, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.write_parquet(path)
    log.info("rates ingested | series=%s rows=%d -> %s", series, out.height, path)
    return path
