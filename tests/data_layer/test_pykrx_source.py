from datetime import date

import polars as pl
import pytest

from data_layer.pykrx_source import (
    PykrxPriceSource,
    PykrxUniverseSource,
    snapshots_to_memberships,
)
from data_layer.universe import members_asof

_OHLCV_COLS = ["date", "open", "high", "low", "close", "volume"]


def _ohlcv_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [date(2024, 1, 2), date(2024, 1, 3)],
            "open": [100.0, 101.0],
            "high": [105.0, 102.0],
            "low": [99.0, 100.0],
            "close": [102.0, 101.0],
            "volume": [1000, 2000],
        }
    )


def test_snapshots_to_memberships_diffs_intervals() -> None:
    snaps = [
        (date(2015, 1, 1), {"A", "B"}),
        (date(2015, 2, 1), {"A", "B"}),
        (date(2015, 3, 1), {"A", "C"}),  # B 편출, C 편입
        (date(2015, 4, 1), {"A", "C"}),
    ]
    got = {(m.symbol, m.added, m.removed) for m in snapshots_to_memberships(snaps)}
    assert got == {
        ("A", date(2015, 1, 1), None),
        ("B", date(2015, 1, 1), date(2015, 3, 1)),
        ("C", date(2015, 3, 1), None),
    }


def test_reentry_creates_two_intervals() -> None:
    snaps = [
        (date(2015, 1, 1), {"A"}),
        (date(2015, 2, 1), {"B"}),  # A 편출
        (date(2015, 3, 1), {"A"}),  # A 재편입
    ]
    a_intervals = sorted(
        (m.added, m.removed) for m in snapshots_to_memberships(snaps) if m.symbol == "A"
    )
    assert a_intervals == [
        (date(2015, 1, 1), date(2015, 2, 1)),
        (date(2015, 3, 1), None),
    ]


def test_fetch_uses_injected_source_and_skips_empty() -> None:
    # 네트워크 호출 대신 주입한 함수로 모킹한다 (실호출 금지)
    def fake(ticker: str, on: date) -> set[str]:
        assert ticker == "1028"  # kospi200
        if on.month == 6:
            return set()  # 휴일/빈 응답 시뮬레이션 → 건너뛰어야 함
        return {"A", "B"} if on < date(2015, 7, 1) else {"A", "C"}

    src = PykrxUniverseSource(
        date(2015, 1, 1), date(2015, 12, 31), sample_days=30, constituents_fn=fake
    )
    members = src.fetch("kospi200")

    assert members_asof(members, "2015-03-15") == {"A", "B"}
    assert members_asof(members, "2015-10-15") == {"A", "C"}
    # A 는 전 구간 유지 — 6월 빈 응답이 구간을 잘못 끊지 않아야 한다
    a = [m for m in members if m.symbol == "A"]
    assert len(a) == 1 and a[0].removed is None


def test_unknown_universe_raises() -> None:
    src = PykrxUniverseSource(date(2015, 1, 1), date(2015, 12, 31))
    with pytest.raises(ValueError):
        src.fetch("sp500")


def test_price_source_joins_raw_close_when_available() -> None:
    def fake(ticker: str, start: date, end: date, adjusted: bool) -> pl.DataFrame:
        f = _ohlcv_frame()
        # 원본가는 수정가보다 높다고 가정(가상)
        return f if adjusted else f.with_columns(pl.col("close") * 1.2)

    df = PykrxPriceSource(ohlcv_fn=fake).fetch("005930", date(2024, 1, 1), date(2024, 1, 31))
    assert "close_raw" in df.columns
    assert df["close_raw"].null_count() == 0
    assert df.sort("date")["close_raw"].to_list() == [102.0 * 1.2, 101.0 * 1.2]


def test_price_source_degrades_when_unadjusted_empty() -> None:
    # pykrx 1.0.51 처럼 adjusted=False 가 비어 오는 환경을 모사
    def fake(ticker: str, start: date, end: date, adjusted: bool) -> pl.DataFrame:
        if not adjusted:
            return pl.DataFrame(schema={c: pl.Float64() for c in _OHLCV_COLS})
        return _ohlcv_frame()

    df = PykrxPriceSource(ohlcv_fn=fake).fetch("005930", date(2024, 1, 1), date(2024, 1, 31))
    assert "close_raw" in df.columns
    assert df["close_raw"].null_count() == df.height  # best-effort: 전부 null
