from datetime import date
from pathlib import Path

import polars as pl
import pytest

from data_layer.ingest import ingest_prices, normalize_prices
from data_layer.loader import RAW_PRICE_SCHEMA, load_prices, prices_path


class _FakePriceSource:
    """네트워크 없는 가격 소스 (테스트용). 둘째 날은 거래정지(거래량 0)."""

    def fetch(self, ticker: str, start: date, end: date) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "date": [date(2020, 1, 2), date(2020, 1, 3)],
                "open": [100.0, 101.0],
                "high": [105.0, 101.0],
                "low": [99.0, 101.0],
                "close": [102.0, 101.0],
                "volume": [1000, 0],  # 둘째 날 무거래 → stg_prices 에서 is_halted=True 파생
                "close_raw": [120.0, 119.0],
            }
        )


def test_normalize_prices_matches_raw_schema() -> None:
    # ELT 패턴: normalize_prices 는 raw 스키마(is_halted 없음)로 정규화한다.
    # is_halted 는 dbt stg_prices 에서 (volume = 0) 으로 파생.
    raw = _FakePriceSource().fetch("AAA", date(2020, 1, 1), date(2020, 1, 31))
    stamped = raw.with_columns(pl.lit("AAA").alias("symbol"), pl.lit("u").alias("universe"))
    out = normalize_prices(stamped)
    assert out.columns == list(RAW_PRICE_SCHEMA)
    assert out.schema == pl.Schema(RAW_PRICE_SCHEMA)
    assert "is_halted" not in out.columns


def test_ingest_writes_raw_prices(tmp_path: Path) -> None:
    # ELT: ingest 는 raw parquet 을 적재한다(is_halted 없음 — dbt 에서 파생).
    ingest_prices(
        _FakePriceSource(),
        "kospi200",
        ["AAA", "BBB"],
        date(2020, 1, 1),
        date(2020, 1, 31),
        data_dir=tmp_path,
    )
    df = pl.read_parquet(prices_path("kospi200", tmp_path))
    assert set(df["universe"].to_list()) == {"kospi200"}
    assert set(df["symbol"].unique().to_list()) == {"AAA", "BBB"}
    assert "close_raw" in df.columns
    assert "is_halted" not in df.columns  # raw 에는 없음 → dbt 에서 파생


def _write_prices_mart(marts: Path) -> None:
    marts.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        {
            "universe": ["kospi200", "kospi200", "other"],
            "symbol": ["AAA", "AAA", "ZZZ"],
            "date": [date(2020, 1, 2), date(2020, 1, 3), date(2020, 1, 2)],
            "close": [102.0, 101.0, 50.0],
        }
    ).write_parquet(marts / "fct_prices.parquet")


def test_load_prices_filters_universe_and_dates(tmp_path: Path) -> None:
    # 소비 레이어(load_prices)는 dbt 마트를 읽고 universe 로 필터.
    marts = tmp_path / "marts"
    _write_prices_mart(marts)

    df = load_prices("kospi200", marts_dir=marts)
    assert set(df["universe"].to_list()) == {"kospi200"}
    assert df.height == 2

    df2 = load_prices("kospi200", start="2020-01-03", marts_dir=marts)
    assert df2["date"].to_list() == [date(2020, 1, 3)]


def test_load_prices_requires_mart(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_prices("does_not_exist", marts_dir=tmp_path)
