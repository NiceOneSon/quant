from datetime import date
from pathlib import Path

import polars as pl
import pytest

from data_layer.fred_source import FredRateSource
from data_layer.ingest import ingest_rates
from data_layer.rates import RAW_RATE_SCHEMA, load_rates, rates_path

_SK_DGS10 = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"  # fake hash for DGS10
_SK_DFF = "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5"      # fake hash for DFF


def _fake_read(series: str, start: date, end: date) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [date(2023, 12, 1), date(2024, 1, 1), date(2024, 2, 1)],
            "rate": [3.65, 3.60, 3.55],
        }
    )


def test_fred_source_returns_date_rate() -> None:
    df = FredRateSource(series="IR3TIB01KRM156N", read_fn=_fake_read).fetch(
        date(2023, 1, 1), date(2024, 3, 1)
    )
    assert df.columns == ["date", "rate"]
    assert df["rate"].to_list() == [3.65, 3.60, 3.55]


def test_ingest_stamps_series_saves_raw(tmp_path: Path) -> None:
    # ELT: ingest 는 date/series/rate 만 저장. country 는 dbt rate_series seed 에서 파생.
    src = FredRateSource(series="IR3TIB01KRM156N", read_fn=_fake_read)
    ingest_rates(src, "IR3TIB01KRM156N", date(2023, 1, 1), date(2024, 3, 1), data_dir=tmp_path)
    df = pl.read_parquet(rates_path("IR3TIB01KRM156N", tmp_path))

    assert df.schema == pl.Schema(RAW_RATE_SCHEMA)
    assert set(df["series"].to_list()) == {"IR3TIB01KRM156N"}
    assert "country" not in df.columns  # raw 에는 없음 → dbt 에서 파생


def test_ingest_sorts_by_date(tmp_path: Path) -> None:
    src = FredRateSource(series="DGS10", read_fn=_fake_read)
    ingest_rates(src, "DGS10", date(2023, 1, 1), date(2024, 3, 1), data_dir=tmp_path)
    df = pl.read_parquet(rates_path("DGS10", tmp_path))
    assert df["date"].to_list() == sorted(df["date"].to_list())


def _write_rates_mart(marts: Path) -> None:
    """fct_rates + dim_rate_series 마트 mock. 스타 스키마: fct 에 series 없음."""
    marts.mkdir(parents=True, exist_ok=True)
    # dim_rate_series: 메타
    pl.DataFrame(
        {
            "sk_id": [_SK_DGS10, _SK_DFF],
            "series": ["DGS10", "DFF"],
            "country": ["US", "US"],
            "label": ["미국채 10년", "미 연방기금금리"],
            "tenor": ["10Y", "O/N"],
        }
    ).write_parquet(marts / "dim_rate_series.parquet")
    # fct_rates: SK + rate 만
    pl.DataFrame(
        {
            "sk_id": ["h1", "h2", "h3"],
            "sk_dim_rate_series": [_SK_DGS10, _SK_DGS10, _SK_DFF],
            "date": [date(2024, 1, 1), date(2024, 2, 1), date(2024, 1, 1)],
            "rate": [4.0, 4.1, 5.3],
        }
    ).write_parquet(marts / "fct_rates.parquet")


def test_load_rates_filters_series_and_dates(tmp_path: Path) -> None:
    marts = tmp_path / "marts"
    _write_rates_mart(marts)

    df = load_rates("DGS10", marts_dir=marts)
    assert set(df["series"].to_list()) == {"DGS10"}
    assert df.height == 2
    assert "label" in df.columns  # dim join 확인

    df2 = load_rates("DGS10", start="2024-02-01", marts_dir=marts)
    assert df2["date"].to_list() == [date(2024, 2, 1)]


def test_load_rates_requires_mart(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_rates("nope", marts_dir=tmp_path)
