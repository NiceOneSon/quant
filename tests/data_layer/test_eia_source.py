from datetime import date

import polars as pl
import pytest

from data_layer.eia_source import EIA_BRENT, EIA_WTI, EiaSeriesSource


def _fake_wti(series: str, start: date, end: date) -> pl.DataFrame:
    assert series == EIA_WTI
    return pl.DataFrame({"date": [date(2024, 1, 2), date(2024, 1, 3)], "value": [72.77, 73.10]})


def _fake_empty(series: str, start: date, end: date) -> pl.DataFrame:
    return pl.DataFrame(schema={"date": pl.Date(), "value": pl.Float64()})


def test_returns_date_value_columns() -> None:
    df = EiaSeriesSource(series=EIA_WTI, read_fn=_fake_wti).fetch(
        date(2024, 1, 1), date(2024, 1, 31)
    )
    assert df.columns == ["date", "value"]
    assert df["value"].to_list() == [72.77, 73.10]


def test_empty_response_returns_correct_schema() -> None:
    df = EiaSeriesSource(series=EIA_WTI, read_fn=_fake_empty).fetch(
        date(2024, 1, 1), date(2024, 1, 5)
    )
    assert df.height == 0
    assert df.schema == pl.Schema({"date": pl.Date(), "value": pl.Float64()})


def test_brent_series_passed_through() -> None:
    received: list[str] = []

    def _capture(series: str, start: date, end: date) -> pl.DataFrame:
        received.append(series)
        return pl.DataFrame({"date": [date(2024, 1, 2)], "value": [78.5]})

    EiaSeriesSource(series=EIA_BRENT, read_fn=_capture).fetch(date(2024, 1, 1), date(2024, 1, 5))
    assert received == [EIA_BRENT]


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EIA_API_KEY", raising=False)
    src = EiaSeriesSource(series=EIA_WTI)
    with pytest.raises(OSError, match="EIA_API_KEY"):
        src.fetch(date(2024, 1, 1), date(2024, 1, 5))
