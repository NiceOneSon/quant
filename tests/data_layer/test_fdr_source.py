from datetime import date

import polars as pl
import pytest

from data_layer.fdr_source import FdrPriceSource, FdrUniverseSource
from data_layer.ingest import normalize_prices
from data_layer.loader import RAW_PRICE_SCHEMA
from data_layer.universe import members_asof


def _fake_read(ticker: str, start: date, end: date) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [date(2024, 1, 2), date(2024, 1, 3)],
            "open": [100.0, 101.0],
            "high": [105.0, 102.0],
            "low": [99.0, 100.0],
            "close": [102.0, 101.0],
            "volume": [1000, 0],  # 둘째 날 무거래
        }
    )


def test_fdr_source_yields_null_close_raw() -> None:
    # FDR 은 수정주가 전용 → close_raw 는 항상 null
    df = FdrPriceSource(read_fn=_fake_read).fetch("005930", date(2024, 1, 1), date(2024, 1, 31))
    assert "close_raw" in df.columns
    assert df["close_raw"].null_count() == df.height
    assert df["close"].to_list() == [102.0, 101.0]


def test_fdr_source_frame_fits_raw_price_schema_after_normalize() -> None:
    # ELT: normalize_prices 는 raw 스키마(is_halted 없음)로 정규화.
    # is_halted 는 dbt stg_prices 에서 (volume = 0) 으로 파생.
    bars = FdrPriceSource(read_fn=_fake_read).fetch("005930", date(2024, 1, 1), date(2024, 1, 31))
    stamped = bars.with_columns(pl.lit("005930").alias("symbol"), pl.lit("kospi").alias("universe"))
    out = normalize_prices(stamped)
    assert out.schema == pl.Schema(RAW_PRICE_SCHEMA)
    assert "is_halted" not in out.columns


def test_fdr_universe_snapshot_at_asof() -> None:
    src = FdrUniverseSource(asof=date(2026, 6, 12), listing_fn=lambda market: ["AAA", "BBB", "AAA"])
    members = src.fetch("kospi")
    assert {m.symbol for m in members} == {"AAA", "BBB"}  # 중복 제거
    # asof 기준 스냅샷: added=asof, removed=None
    assert all(m.added == date(2026, 6, 12) and m.removed is None for m in members)
    # asof 당일/이후엔 보이고, 이전엔 비어 있다(스냅샷 한계)
    assert members_asof(members, "2026-06-12") == {"AAA", "BBB"}
    assert members_asof(members, "2026-06-11") == set()


def test_fdr_universe_rejects_index_names() -> None:
    src = FdrUniverseSource(asof=date(2026, 6, 12))
    with pytest.raises(ValueError):
        src.fetch("kospi200")  # FDR 은 지수 구성종목 미지원
