"""데이터 수집 진입점. 유니버스 멤버십, 가격(OHLCV), 금리, 매크로 시계열을 적재한다.

사용법:
  # 1) 유니버스 멤버십
  uv run python scripts/ingest.py --config configs/backtest.yaml --dataset universe --source fdr
  uv run python scripts/ingest.py --config configs/backtest.yaml --dataset universe --source csv
  # 2) 가격 — 유니버스 편입 이력 전체(상장폐지 포함)
  uv run python scripts/ingest.py --config configs/backtest.yaml --dataset prices --source fdr
  # 3) 금리 — 특정 시리즈 또는 seed(rate_series.csv) 전체
  uv run python scripts/ingest.py --config configs/backtest.yaml --dataset rates --series DGS10
  uv run python scripts/ingest.py --config configs/backtest.yaml --dataset rates  # seed 전체 일괄
  # 4) 매크로/FX/원자재/지수 — 특정 시리즈 또는 seed(macro_series.csv) 전체
  uv run python scripts/ingest.py --config configs/backtest.yaml \
      --dataset macro --source fdr --series USD/KRW
  uv run python scripts/ingest.py --config configs/backtest.yaml --dataset macro  # seed 전체 일괄

저장: 유니버스 → data/reference/universe/<universe>.parquet
      가격     → data/processed/prices/<universe>.parquet
      금리     → data/reference/rates/<series>.parquet
      매크로   → data/reference/macro/<series>.parquet  (슬래시 → 언더스코어)
pykrx/fdr 소스는 `uv sync --extra data` 필요.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

from common.config import AppConfig, load_config
from common.logging import get_logger
from data_layer.fred_source import DEFAULT_RISK_FREE_SERIES
from data_layer.ingest import (
    ingest_macro,
    ingest_prices,
    ingest_rates,
    ingest_securities,
    ingest_universe,
    ingest_universe_snapshot,
)
from data_layer.sources import CsvUniverseSource, PriceSource, UniverseSource
from data_layer.universe import DEFAULT_DATA_DIR, universe_path

log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SEED_MACRO = _REPO_ROOT / "dbt" / "seeds" / "macro_series.csv"
_SEED_RATES = _REPO_ROOT / "dbt" / "seeds" / "rate_series.csv"


def _read_macro_seed() -> list[dict[str, str]]:
    with _SEED_MACRO.open(newline="") as f:
        return list(csv.DictReader(f))


def _read_rate_seed() -> list[dict[str, str]]:
    with _SEED_RATES.open(newline="") as f:
        return list(csv.DictReader(f))


def _ingest_universe(config: AppConfig, source_kind: str) -> None:
    universe = config.data.universe
    if source_kind == "fdr":
        # FDR StockListing 은 현재 스냅샷만 → 시점마다 누적해 PIT 멤버십을 재구성.
        # asof=종료일. 주기적으로 실행할수록 편출·상폐가 반영됨. 시장 단위만(kospi/kosdaq/krx).
        from data_layer.fdr_source import FdrUniverseSource

        asof = date.fromisoformat(config.data.end_date)
        path = ingest_universe_snapshot(FdrUniverseSource(asof=asof), universe, asof)
        log.info("done | dataset=universe source=fdr (snapshot accumulate) path=%s", path)
        return

    if source_kind == "csv":
        source: UniverseSource = CsvUniverseSource(DEFAULT_DATA_DIR / "raw" / "universe")
    else:  # pykrx — 현재 KRX 지수 endpoint 회귀로 동작 안 함(fdr 권장)
        from data_layer.pykrx_source import PykrxUniverseSource

        source = PykrxUniverseSource(
            start=date.fromisoformat(config.data.start_date),
            end=date.fromisoformat(config.data.end_date),
        )
    path = ingest_universe(source, universe)
    log.info("done | dataset=universe source=%s path=%s", source_kind, path)


def _ingest_prices(config: AppConfig, source_kind: str) -> None:
    if source_kind == "pykrx":
        from data_layer.pykrx_source import PykrxPriceSource

        price_source: PriceSource = PykrxPriceSource()
    elif source_kind == "fdr":
        from data_layer.fdr_source import FdrPriceSource

        price_source = FdrPriceSource()
    else:
        raise ValueError("가격 수집은 pykrx 또는 fdr 소스만 지원합니다.")

    universe = config.data.universe
    # 가격 수집은 dbt 이전 단계 → raw 유니버스(universe_path)에서 종목 목록을 읽는다.
    # (상장폐지 포함 → 생존편향 방지)
    import polars as pl

    raw_universe = pl.read_parquet(universe_path(universe))
    tickers = sorted(raw_universe["symbol"].unique().to_list())
    path = ingest_prices(
        price_source,
        universe,
        tickers,
        start=date.fromisoformat(config.data.start_date),
        end=date.fromisoformat(config.data.end_date),
    )
    log.info("done | dataset=prices source=%s tickers=%d path=%s", source_kind, len(tickers), path)


def _ingest_one_rate(config: AppConfig, series: str) -> None:
    from data_layer.fred_source import FredRateSource

    path = ingest_rates(
        FredRateSource(series=series),
        series,
        start=date.fromisoformat(config.data.start_date),
        end=date.fromisoformat(config.data.end_date),
    )
    log.info("done | dataset=rates source=fred series=%s path=%s", series, path)


def _ingest_rates(config: AppConfig, series: str | None) -> None:
    if series:
        _ingest_one_rate(config, series)
        return
    # batch: seed 전체
    rows = _read_rate_seed()
    log.info("batch rates | seed=%s rows=%d", _SEED_RATES, len(rows))
    for row in rows:
        try:
            _ingest_one_rate(config, row["series"])
        except Exception:
            log.exception("failed | series=%s", row["series"])


def _ingest_securities(source_kind: str, market: str) -> None:
    if source_kind != "fdr":
        raise ValueError("종목 마스터는 현재 fdr 소스만 지원합니다.")
    from data_layer.fdr_source import FdrSecuritySource

    path = ingest_securities(FdrSecuritySource(), market)
    log.info("done | dataset=securities source=fdr market=%s path=%s", market, path)


def _ingest_one_macro(config: AppConfig, source_kind: str, series: str) -> None:
    if source_kind == "fdr":
        from data_layer.fdr_source import FdrSeriesSource

        source = FdrSeriesSource(series=series)
    elif source_kind == "fred":
        from data_layer.fred_source import FredSeriesSource

        source = FredSeriesSource(series=series)
    elif source_kind == "ecos":
        from data_layer.ecos_source import EcosSeriesSource

        source = EcosSeriesSource(series=series)
    else:
        raise ValueError("매크로는 fdr, fred, ecos 소스만 지원합니다.")

    path = ingest_macro(
        source,
        series,
        start=date.fromisoformat(config.data.start_date),
        end=date.fromisoformat(config.data.end_date),
    )
    log.info("done | dataset=macro source=%s series=%s path=%s", source_kind, series, path)


def _ingest_macro(config: AppConfig, source_kind: str | None, series: str | None) -> None:
    if series and source_kind:
        _ingest_one_macro(config, source_kind, series)
        return
    if series and not source_kind:
        raise ValueError("--series 지정 시 --source (fdr|fred) 도 필요합니다.")
    # batch: seed 전체 (source 컬럼 우선, 없으면 --source 폴백)
    rows = _read_macro_seed()
    log.info("batch macro | seed=%s rows=%d", _SEED_MACRO, len(rows))
    for row in rows:
        src = row.get("source") or source_kind
        if not src:
            log.warning("skip | series=%s — source 불명 (seed에 source 컬럼 없음)", row["series"])
            continue
        try:
            _ingest_one_macro(config, src, row["series"])
        except Exception:
            log.exception("failed | source=%s series=%s", src, row["series"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="설정 이름 또는 경로 (예: dev)")
    parser.add_argument(
        "--dataset",
        choices=["universe", "prices", "rates", "securities", "macro"],
        default="universe",
        help="수집 대상",
    )
    parser.add_argument(
        "--source",
        choices=["csv", "pykrx", "fdr", "fred", "ecos"],
        default=None,
        help="수집 소스 (macro/rates 단일 시리즈 시 필요; 배치 모드는 seed의 source 컬럼 사용)",
    )
    parser.add_argument(
        "--series",
        default=None,
        help="수집할 시리즈. 생략하면 dbt seed CSV 전체를 일괄 수집(macro/rates 전용).",
    )
    parser.add_argument("--market", default="kospi", help="종목 마스터 시장 (securities 용)")
    args = parser.parse_args()

    name = args.config.split("/")[-1].replace(".yaml", "")
    config = load_config(name)

    if args.dataset == "universe":
        _ingest_universe(config, args.source or "csv")
    elif args.dataset == "prices":
        _ingest_prices(config, args.source or "fdr")
    elif args.dataset == "rates":
        _ingest_rates(config, args.series)
    elif args.dataset == "macro":
        _ingest_macro(config, args.source, args.series)
    else:
        _ingest_securities(args.source or "fdr", args.market)


if __name__ == "__main__":
    main()
