from datetime import date

import polars as pl
import pytest

from research.signals.momentum import Momentum


def _frame() -> pl.DataFrame:
    rows = []
    series = {
        "UP": [100.0, 110.0, 121.0],  # +21% over 2 steps
        "DOWN": [100.0, 90.0, 81.0],  # -19%
        "SHORTHIST": [100.0, 100.0],  # 이력 부족
    }
    days = [date(2020, 1, 2), date(2020, 1, 3), date(2020, 1, 6)]
    for sym, closes in series.items():
        for d, c in zip(days[: len(closes)], closes, strict=False):
            rows.append({"date": d, "symbol": sym, "close": c})
    return pl.DataFrame(rows)


def test_momentum_scores_and_skips_short_history() -> None:
    scores = Momentum(lookback=2, skip=0).generate(_frame())
    assert set(scores) == {"UP", "DOWN"}  # 이력 부족 종목 제외
    assert scores["UP"] == pytest.approx(0.21)
    assert scores["DOWN"] == pytest.approx(-0.19)
