"""데이터 수집 진입점. 유니버스 멤버십과 가격(OHLCV)을 point-in-time 로 적재한다.

사용법:
  # 1) 유니버스 멤버십
  #  - fdr : 현재 상장목록 스냅샷을 누적(앞으로 쌓임). 시장 단위만(kospi/kosdaq/krx).
  #  - csv : 과거 멤버십 이력을 직접 주입(과거 백테스트 즉시 가능). 상폐 종목 포함.
  #          data/raw/universe/<universe>.csv, 헤더 symbol,added,removed (재편입은 여러 행).
  uv run python scripts/ingest.py --config configs/backtest.yaml --dataset universe --source fdr
  uv run python scripts/ingest.py --config configs/backtest.yaml --dataset universe --source csv
  # 2) 가격 — 유니버스에 한 번이라도 편입된 모든 종목의 OHLCV (상장폐지 포함)
  uv run python scripts/ingest.py --config configs/backtest.yaml --dataset prices --source pykrx
  # 3) 무위험금리 (FRED, API 키 불필요)
  uv run python scripts/ingest.py --config configs/backtest.yaml --dataset rates --source fred

config.data.universe 이름과 config.data 의 기간을 사용한다.
저장: 유니버스 → data/reference/universe/<universe>.parquet,
      가격     → data/processed/prices/<universe>.parquet,
      금리     → data/reference/rates/<series>.parquet.
pykrx/fdr 소스는 `uv sync --extra data` 필요.
"""

from __future__ import annotations

import argparse
from datetime import date

from common.config import AppConfig, load_config
from common.logging import get_logger
from data_layer.fred_source import DEFAULT_RISK_FREE_SERIES
from data_layer.ingest import (
    ingest_prices,
    ingest_rates,
    ingest_universe,
    ingest_universe_snapshot,
)
from data_layer.sources import CsvUniverseSource, PriceSource, UniverseSource
from data_layer.universe import DEFAULT_DATA_DIR, universe_path

log = get_logger(__name__)


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


def _ingest_rates(config: AppConfig, source_kind: str, series: str) -> None:
    if source_kind != "fred":
        raise ValueError("금리는 현재 fred 소스만 지원합니다.")
    from data_layer.fred_source import FredRateSource

    path = ingest_rates(
        FredRateSource(series=series),
        series,
        start=date.fromisoformat(config.data.start_date),
        end=date.fromisoformat(config.data.end_date),
    )
    log.info("done | dataset=rates source=%s series=%s path=%s", source_kind, series, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="설정 이름 또는 경로 (예: dev)")
    parser.add_argument(
        "--dataset",
        choices=["universe", "prices", "rates"],
        default="universe",
        help="수집 대상",
    )
    parser.add_argument(
        "--source", choices=["csv", "pykrx", "fdr", "fred"], default="csv", help="수집 소스"
    )
    parser.add_argument(
        "--series", default=DEFAULT_RISK_FREE_SERIES, help="FRED 금리 시리즈 (rates 용)"
    )
    args = parser.parse_args()

    name = args.config.split("/")[-1].replace(".yaml", "")
    config = load_config(name)

    if args.dataset == "universe":
        _ingest_universe(config, args.source)
    elif args.dataset == "prices":
        _ingest_prices(config, args.source)
    else:
        _ingest_rates(config, args.source, args.series)


if __name__ == "__main__":
    main()
