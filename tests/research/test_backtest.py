from datetime import date

import polars as pl

from data_layer.universe import Membership
from portfolio.optimizer import PortfolioConstraints
from research.backtest import simulate
from research.signals.momentum import Momentum


def _prices() -> pl.DataFrame:
    # 2개월에 걸친 10거래일. UP 상승, DOWN 하락, FLAT 횡보.
    days = [date(2020, 1, d) for d in (2, 3, 6, 7, 8)] + [date(2020, 2, d) for d in (3, 4, 5, 6, 7)]
    paths = {
        "UP": [100.0 * (1.05**i) for i in range(10)],
        "DOWN": [100.0 * (0.95**i) for i in range(10)],
        "FLAT": [100.0 for _ in range(10)],
    }
    rows = []
    for sym, closes in paths.items():
        for d, c in zip(days, closes, strict=True):
            rows.append({"date": d, "symbol": sym, "open": c, "close": c, "is_halted": False})
    return pl.DataFrame(rows)


def _members() -> list[Membership]:
    return [Membership(s, added=date(2019, 1, 1)) for s in ("UP", "DOWN", "FLAT")]


def _run(commission_bps: float, slippage_bps: float) -> dict[str, float]:
    return simulate(
        _prices(),
        _members(),
        signal=Momentum(lookback=3, skip=0),
        constraints=PortfolioConstraints(max_weight=1.0),
        initial_capital=1_000_000.0,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
        top_n=1,
    )


def test_simulate_runs_and_picks_uptrend() -> None:
    m = _run(commission_bps=5.0, slippage_bps=2.0)
    assert m["n_days"] == 10.0
    # 모멘텀이 UP 을 골라 진입 → 상승장에서 최종 자산 > 초기자본
    assert m["final_value"] > 1_000_000.0
    assert m["total_return"] > 0.0


def test_costs_reduce_return() -> None:
    free = _run(commission_bps=0.0, slippage_bps=0.0)
    costly = _run(commission_bps=500.0, slippage_bps=500.0)
    # 거래비용이 있으면 동일 전략의 최종 자산이 더 낮아야 한다
    assert costly["final_value"] < free["final_value"]
