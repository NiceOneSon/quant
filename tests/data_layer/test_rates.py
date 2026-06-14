from datetime import date
from pathlib import Path

import polars as pl
import pytest

from data_layer.fred_source import FredRateSource
from data_layer.ingest import ingest_rates
from data_layer.rates import RATE_SCHEMA, load_rates, rates_path


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
    # ingest 는 raw parquet 적재(series/country stamp). raw 직접 검증.
    src = FredRateSource(series="IR3TIB01KRM156N", read_fn=_fake_read)
    ingest_rates(src, "IR3TIB01KRM156N", date(2023, 1, 1), date(2024, 3, 1), data_dir=tmp_path)
    df = pl.read_parquet(rates_path("IR3TIB01KRM156N", tmp_path))

    assert df.schema == pl.Schema(RATE_SCHEMA)
    assert set(df["series"].to_list()) == {"IR3TIB01KRM156N"}
    assert set(df["country"].to_list()) == {"KR"}  # 한국 시리즈로 구분됨


def test_us_series_tagged_us(tmp_path: Path) -> None:
    src = FredRateSource(read_fn=_fake_read)
    ingest_rates(src, "DGS10", date(2023, 1, 1), date(2024, 3, 1), data_dir=tmp_path)
    df = pl.read_parquet(rates_path("DGS10", tmp_path))
    assert set(df["country"].to_list()) == {"US"}  # 미국채로 구분됨


def test_unknown_series_country_na(tmp_path: Path) -> None:
    src = FredRateSource(read_fn=_fake_read)
    ingest_rates(src, "rf", date(2023, 1, 1), date(2024, 3, 1), data_dir=tmp_path)
    df = pl.read_parquet(rates_path("rf", tmp_path))
    assert set(df["country"].to_list()) == {"NA"}  # 미등록 → NA


def _write_rates_mart(marts: Path) -> None:
    marts.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        {
            "date": [date(2024, 1, 1), date(2024, 2, 1), date(2024, 1, 1)],
            "series": ["DGS10", "DGS10", "DFF"],
            "country": ["US", "US", "US"],
            "rate": [4.0, 4.1, 5.3],
        }
    ).write_parquet(marts / "fct_rates.parquet")


def test_load_rates_filters_series_and_dates(tmp_path: Path) -> None:
    marts = tmp_path / "marts"
    _write_rates_mart(marts)

    df = load_rates("DGS10", marts_dir=marts)
    assert set(df["series"].to_list()) == {"DGS10"}  # DFF 제외
    assert df.height == 2

    df2 = load_rates("DGS10", start="2024-02-01", marts_dir=marts)
    assert df2["date"].to_list() == [date(2024, 2, 1)]


def test_load_rates_requires_mart(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_rates("nope", marts_dir=tmp_path)
