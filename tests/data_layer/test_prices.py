from datetime import date
from pathlib import Path

import polars as pl
import pytest

from data_layer.ingest import ingest_prices, normalize_prices
from data_layer.loader import PRICE_SCHEMA, load_prices


class _FakePriceSource:
    """네트워크 없는 가격 소스 (테스트용). 둘째 날은 거래정지(거래량 0)."""

    def fetch(self, ticker: str, start: date, end: date) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "date": [date(2020, 1, 2), date(2020, 1, 3)],
                "open": [100.0, 101.0],
                "high": [105.0, 101.0],
                "low": [99.0, 101.0],
                "close": [102.0, 101.0],  # 수정주가
                "volume": [1000, 0],  # 둘째 날 무거래 → halted
                "close_raw": [120.0, 119.0],  # 원본 종가(수정계수 복원용)
            }
        )


def test_normalize_prices_flags_halt_and_matches_schema() -> None:
    raw = _FakePriceSource().fetch("AAA", date(2020, 1, 1), date(2020, 1, 31))
    stamped = raw.with_columns(pl.lit("AAA").alias("symbol"), pl.lit("u").alias("universe"))
    out = normalize_prices(stamped)
    assert out.columns == list(PRICE_SCHEMA)
    assert out.schema == pl.Schema(PRICE_SCHEMA)
    assert out["is_halted"].to_list() == [False, True]


def test_ingest_load_roundtrip(tmp_path: Path) -> None:
    ingest_prices(
        _FakePriceSource(),
        "kospi200",
        ["AAA", "BBB"],
        date(2020, 1, 1),
        date(2020, 1, 31),
        data_dir=tmp_path,
    )
    df = load_prices("kospi200", data_dir=tmp_path)

    assert set(df["universe"].to_list()) == {"kospi200"}  # 명시적 유니버스 키
    assert set(df["symbol"].unique().to_list()) == {"AAA", "BBB"}
    assert df.filter(pl.col("symbol") == "AAA").height == 2
    # 원본 종가가 함께 저장돼 수정계수(close/close_raw) 복원이 가능해야 한다
    assert "close_raw" in df.columns
    # 거래정지일이 표시돼야 한다
    assert df.filter(pl.col("is_halted"))["volume"].to_list() == [0, 0]


def test_load_prices_date_filter(tmp_path: Path) -> None:
    ingest_prices(
        _FakePriceSource(),
        "kospi200",
        ["AAA"],
        date(2020, 1, 1),
        date(2020, 1, 31),
        data_dir=tmp_path,
    )
    df = load_prices("kospi200", start="2020-01-03", data_dir=tmp_path)
    assert df["date"].to_list() == [date(2020, 1, 3)]


def test_load_missing_prices_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_prices("does_not_exist", data_dir=tmp_path)
