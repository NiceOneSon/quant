from datetime import date
from pathlib import Path

import polars as pl
import pytest

from data_layer.fred_source import FredRateSource
from data_layer.ingest import ingest_rates
from data_layer.rates import RATE_SCHEMA, load_rates


def _fake_read(series: str, start: date, end: date) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [date(2023, 12, 1), date(2024, 1, 1), date(2024, 2, 1)],
            "rate": [3.65, 3.60, 3.55],  # 연율 %
        }
    )


def test_fred_source_returns_date_rate() -> None:
    df = FredRateSource(series="IR3TIB01KRM156N", read_fn=_fake_read).fetch(
        date(2023, 1, 1), date(2024, 3, 1)
    )
    assert df.columns == ["date", "rate"]
    assert df["rate"].to_list() == [3.65, 3.60, 3.55]


def test_ingest_stamps_series_and_country(tmp_path: Path) -> None:
    source = FredRateSource(series="IR3TIB01KRM156N", read_fn=_fake_read)
    ingest_rates(source, "IR3TIB01KRM156N", date(2023, 1, 1), date(2024, 3, 1), data_dir=tmp_path)
    df = load_rates("IR3TIB01KRM156N", data_dir=tmp_path)

    assert df.schema == pl.Schema(RATE_SCHEMA)
    assert df.height == 3
    assert set(df["series"].to_list()) == {"IR3TIB01KRM156N"}
    assert set(df["country"].to_list()) == {"KR"}  # 한국 시리즈로 구분됨
    assert df.sort("date")["rate"].to_list() == [3.65, 3.60, 3.55]


def test_us_series_tagged_us(tmp_path: Path) -> None:
    src = FredRateSource(read_fn=_fake_read)
    ingest_rates(src, "DGS10", date(2023, 1, 1), date(2024, 3, 1), data_dir=tmp_path)
    df = load_rates("DGS10", data_dir=tmp_path)
    assert set(df["country"].to_list()) == {"US"}  # 미국채로 구분됨


def test_unknown_series_country_na(tmp_path: Path) -> None:
    src = FredRateSource(read_fn=_fake_read)
    ingest_rates(src, "rf", date(2023, 1, 1), date(2024, 3, 1), data_dir=tmp_path)
    df = load_rates("rf", data_dir=tmp_path)
    assert set(df["country"].to_list()) == {"NA"}  # 미등록 → NA


def test_load_rates_date_filter(tmp_path: Path) -> None:
    source = FredRateSource(read_fn=_fake_read)
    ingest_rates(source, "rf", date(2023, 1, 1), date(2024, 3, 1), data_dir=tmp_path)
    df = load_rates("rf", start="2024-01-01", data_dir=tmp_path)
    assert df["date"].to_list() == [date(2024, 1, 1), date(2024, 2, 1)]


def test_load_missing_rates_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_rates("nope", data_dir=tmp_path)
