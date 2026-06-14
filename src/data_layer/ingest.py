"""유니버스 수집(ingest). 소스에서 멤버십을 받아 정규화 후 reference parquet 으로 저장한다.

부수효과(파일 쓰기)는 여기로 격리한다. 정규화/검증은 순수 함수(normalize_memberships)로
분리해 테스트한다.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from common.logging import get_logger
from data_layer.loader import RAW_PRICE_SCHEMA, prices_path
from data_layer.rates import RAW_RATE_SCHEMA, rates_path
from data_layer.securities import SECURITY_SCHEMA, securities_path
from data_layer.sources import MacroSource, PriceSource, RateSource, SecuritySource, UniverseSource
from data_layer.universe import (
    DEFAULT_DATA_DIR,
    Membership,
    memberships_to_frame,
    universe_path,
)
from data_layer.universe_snapshots import rebuild_universe, record_snapshot

log = get_logger(__name__)

# 매크로/FX/원자재/지수 시계열 raw 스키마.
# country·label·category 는 dbt macro_series seed 조인으로 파생 → ELT 패턴.
RAW_MACRO_SCHEMA: dict[str, pl.DataType] = {
    "date": pl.Date(),
    "series": pl.String(),
    "value": pl.Float64(),
}


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
    """가격 프레임을 raw 저장 스키마로 정규화한다 (순수).

    ELT 패턴: is_halted 는 dbt stg_prices 에서 (volume = 0) 으로 파생한다.
    여기서는 컬럼 순서·타입 정규화와 (symbol, date) 정렬만 수행한다.
    """
    return (
        frame.select(list(RAW_PRICE_SCHEMA))
        .cast(RAW_PRICE_SCHEMA)  # type: ignore[arg-type]
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
        out = pl.DataFrame(schema=RAW_PRICE_SCHEMA)

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
    """금리 시리즈를 수집해 reference parquet 으로 저장한다 (date, series, rate).

    ELT 패턴: country·label·tenor 는 dbt int_rates_enriched 에서 rate_series seed 조인으로 파생.
    """
    frame = source.fetch(start, end)  # date, rate
    out = (
        frame.with_columns(pl.lit(series).alias("series"))
        .select(list(RAW_RATE_SCHEMA))
        .cast(RAW_RATE_SCHEMA)  # type: ignore[arg-type]
        .sort("date")
    )
    path = rates_path(series, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.write_parquet(path)
    log.info("rates ingested | series=%s rows=%d -> %s", series, out.height, path)
    return path


def macro_path(series: str, data_dir: Path | None = None) -> Path:
    """`series` 매크로 데이터의 parquet 경로 (슬래시 → 언더스코어)."""
    safe = series.replace("/", "_")
    return (data_dir or DEFAULT_DATA_DIR) / "reference" / "macro" / f"{safe}.parquet"


def ingest_macro(
    source: MacroSource,
    series: str,
    start: date,
    end: date,
    *,
    data_dir: Path | None = None,
) -> Path:
    """매크로/FX/원자재/지수 시계열을 수집해 reference parquet 으로 저장한다 (date, series, value).

    ELT 패턴: country·label·category 는 dbt fct_macro 에서 macro_series seed 조인으로 파생.
    """
    frame = source.fetch(start, end)  # date, value
    out = (
        frame.with_columns(pl.lit(series).alias("series"))
        .select(list(RAW_MACRO_SCHEMA))
        .cast(RAW_MACRO_SCHEMA)  # type: ignore[arg-type]
        .sort("date")
    )
    path = macro_path(series, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.write_parquet(path)
    log.info("macro ingested | series=%s rows=%d -> %s", series, out.height, path)
    return path


def ingest_securities(
    source: SecuritySource,
    name: str,
    *,
    data_dir: Path | None = None,
) -> Path:
    """종목 마스터(symbol→name, market)를 수집해 reference parquet 으로 저장한다."""
    df = source.fetch(name)
    out = (
        df.select(list(SECURITY_SCHEMA))
        .unique(subset=["symbol"])
        .cast(SECURITY_SCHEMA)  # type: ignore[arg-type]
        .sort("symbol")
    )
    path = securities_path(name, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.write_parquet(path)
    log.info("securities ingested | name=%s rows=%d -> %s", name, out.height, path)
    return path
