from datetime import date
from pathlib import Path

import polars as pl
import pytest

from data_layer.fdr_source import FdrSeriesSource
from data_layer.fred_source import FredSeriesSource
from data_layer.ingest import RAW_MACRO_SCHEMA, ingest_macro, macro_path
from data_layer.macro import load_macro

_SK_USD_KRW = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"  # fake hash for USD/KRW
_SK_KS11 = "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5"      # fake hash for KS11


def _fake_series(series: str, start: date, end: date) -> pl.DataFrame:
    return pl.DataFrame({"date": [date(2024, 1, 2), date(2024, 1, 3)], "value": [1300.0, 1305.5]})


def _fake_fred(series: str, start: date, end: date) -> pl.DataFrame:
    return pl.DataFrame({"date": [date(2024, 1, 2), date(2024, 1, 3)], "rate": [75.0, 75.5]})


def test_fdr_series_source_returns_date_value() -> None:
    df = FdrSeriesSource(series="USD/KRW", read_fn=_fake_series).fetch(
        date(2024, 1, 1), date(2024, 1, 31)
    )
    assert df.columns == ["date", "value"]
    assert df["value"].to_list() == [1300.0, 1305.5]


def test_fred_series_source_returns_date_value() -> None:
    df = FredSeriesSource(series="DTWEXBGS", read_fn=_fake_fred).fetch(
        date(2024, 1, 1), date(2024, 1, 31)
    )
    assert df.columns == ["date", "value"]
    assert df["value"].to_list() == [75.0, 75.5]


def test_ingest_macro_writes_raw_schema(tmp_path: Path) -> None:
    # ELT: ingest 는 date/series/value 만 저장. label·country 는 dbt 에서 파생.
    src = FdrSeriesSource(series="USD/KRW", read_fn=_fake_series)
    ingest_macro(src, "USD/KRW", date(2024, 1, 1), date(2024, 1, 31), data_dir=tmp_path)

    path = macro_path("USD/KRW", tmp_path)
    assert path.name == "USD_KRW.parquet"  # 슬래시 → 언더스코어
    df = pl.read_parquet(path)
    assert df.schema == pl.Schema(RAW_MACRO_SCHEMA)
    assert set(df["series"].to_list()) == {"USD/KRW"}
    assert "country" not in df.columns


def _write_macro_mart(marts: Path) -> None:
    """fct_macro + dim_macro_series 마트 mock. 스타 스키마: fct 에 series 없음."""
    marts.mkdir(parents=True, exist_ok=True)
    # dim_macro_series: 메타 (series/label/category/unit/country)
    pl.DataFrame(
        {
            "sk_id": [_SK_USD_KRW, _SK_KS11],
            "series": ["USD/KRW", "KS11"],
            "label": ["달러-원 환율", "KOSPI 지수"],
            "unit": ["KRW", "point"],
            "country": ["KR", "KR"],
            "category": ["fx", "index"],
            "source": ["fdr", "fdr"],
        }
    ).write_parquet(marts / "dim_macro_series.parquet")
    # fct_macro: SK + 측정값만
    pl.DataFrame(
        {
            "sk_id": ["h1", "h2", "h3"],
            "sk_dim_macro_series": [_SK_USD_KRW, _SK_USD_KRW, _SK_KS11],
            "date": [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 2)],
            "value": [1300.0, 1305.5, 2500.0],
        }
    ).write_parquet(marts / "fct_macro.parquet")


def test_load_macro_filters_series(tmp_path: Path) -> None:
    marts = tmp_path / "marts"
    _write_macro_mart(marts)

    df = load_macro("USD/KRW", marts_dir=marts)
    assert set(df["series"].to_list()) == {"USD/KRW"}
    assert df.height == 2
    assert "label" in df.columns  # dim join 확인

    df2 = load_macro("USD/KRW", start="2024-01-03", marts_dir=marts)
    assert df2["date"].to_list() == [date(2024, 1, 3)]


def test_load_macro_requires_mart(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_macro("USD/KRW", marts_dir=tmp_path)
