"""백테스트 엔진 (수직 슬라이스).

흐름(PIT-안전): 리밸런싱 시점 t 에서 t 이하 데이터로만 시그널·목표비중을 정하고,
**다음 거래일 시가**에 거래비용·슬리피지를 반영해 체결한다. 거래정지 종목은 체결 제외.

- run_backtest(config): 설정으로 데이터를 로드해 simulate 를 호출하는 IO 래퍼.
- simulate(...): 데이터를 인자로 받는 순수-ish 엔진(네트워크 없음, 테스트 가능).
무비용 백테스트 금지 — commission_bps/slippage_bps 를 항상 반영한다.
"""

from __future__ import annotations

import math
from datetime import date

import polars as pl

from common.config import AppConfig
from common.logging import get_logger
from data_layer.loader import load_prices
from data_layer.universe import Membership, load_universe, members_asof
from portfolio.optimizer import PortfolioConstraints, optimize
from research.signals import Signal
from research.signals.momentum import Momentum

log = get_logger(__name__)


def _monthly_rebalance_dates(dates: list[date]) -> set[date]:
    """각 (연,월)의 첫 거래일을 리밸런싱일로 반환한다."""
    seen: set[tuple[int, int]] = set()
    rebal: set[date] = set()
    for d in dates:
        ym = (d.year, d.month)
        if ym not in seen:
            seen.add(ym)
            rebal.add(d)
    return rebal


def _execute(
    target_w: dict[str, float],
    open_px: dict[str, float],
    halted: dict[str, bool],
    cash: float,
    shares: dict[str, float],
    pv: float,
    cost_rate: float,
) -> tuple[float, dict[str, float]]:
    """목표 비중으로 시가 체결한다. 거래정지·가격없음 종목은 기존 포지션 유지."""
    new_shares = dict(shares)
    for sym in set(target_w) | set(shares):
        price = open_px.get(sym)
        if price is None or price <= 0 or halted.get(sym, False):
            continue  # 거래 불가
        target_sh = (pv * target_w.get(sym, 0.0)) / price
        trade = target_sh - shares.get(sym, 0.0)
        if abs(trade) < 1e-9:
            new_shares[sym] = target_sh
            continue
        cash -= trade * price  # 매수면 현금 감소, 매도면 증가
        cash -= abs(trade) * price * cost_rate  # 수수료+슬리피지
        new_shares[sym] = target_sh
    return cash, {s: v for s, v in new_shares.items() if abs(v) > 1e-9}


def _portfolio_value(cash: float, shares: dict[str, float], px: dict[str, float]) -> float:
    held = 0.0
    for sym, sh in shares.items():
        price = px.get(sym)
        if price is not None and price > 0:
            held += sh * price
    return cash + held


def _metrics(
    equity: list[tuple[date, float]], risk_free: float = 0.0, periods: int = 252
) -> dict[str, float]:
    """일별 자산곡선에서 성과지표를 계산한다 (risk_free 는 연율 fraction)."""
    pvs = [v for _, v in equity]
    if len(pvs) < 2 or pvs[0] <= 0:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "vol": 0.0,
            "sharpe": 0.0,
            "mdd": 0.0,
            "final_value": pvs[-1] if pvs else 0.0,
            "n_days": float(len(pvs)),
        }
    rets = [pvs[i] / pvs[i - 1] - 1.0 for i in range(1, len(pvs))]
    n = len(rets)
    total_return = pvs[-1] / pvs[0] - 1.0
    cagr = (pvs[-1] / pvs[0]) ** (periods / n) - 1.0
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1) if n > 1 else 0.0
    vol = math.sqrt(var) * math.sqrt(periods)
    sharpe = (mean * periods - risk_free) / vol if vol > 0 else 0.0
    peak = pvs[0]
    mdd = 0.0
    for v in pvs:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    return {
        "total_return": total_return,
        "cagr": cagr,
        "vol": vol,
        "sharpe": sharpe,
        "mdd": mdd,
        "final_value": pvs[-1],
        "n_days": float(len(pvs)),
    }


def simulate(
    prices: pl.DataFrame,
    memberships: list[Membership],
    *,
    signal: Signal,
    constraints: PortfolioConstraints,
    initial_capital: float,
    commission_bps: float,
    slippage_bps: float,
    top_n: int,
    risk_free: float = 0.0,
) -> dict[str, float]:
    """PIT-안전 백테스트를 돌리고 성과지표를 반환한다.

    각 리밸런싱일 t: 시그널은 prices(<= t)·members_asof(t) 만 본다 → 결정은 다음 거래일
    시가에 체결(거래비용 반영). 거래정지일은 체결 제외.
    """
    cost_rate = (commission_bps + slippage_bps) / 10_000.0
    close = prices.pivot(on="symbol", index="date", values="close").sort("date")
    open_ = prices.pivot(on="symbol", index="date", values="open").sort("date")
    halt = prices.pivot(on="symbol", index="date", values="is_halted").sort("date")
    close_rows = close.to_dicts()
    open_rows = open_.to_dicts()
    halt_rows = halt.to_dicts()
    dates: list[date] = close["date"].to_list()
    rebal = _monthly_rebalance_dates(dates)

    cash = initial_capital
    shares: dict[str, float] = {}
    equity: list[tuple[date, float]] = []
    pending: dict[str, float] | None = None

    for i, d in enumerate(dates):
        crow = {k: v for k, v in close_rows[i].items() if k != "date"}
        orow = {k: v for k, v in open_rows[i].items() if k != "date"}
        hrow = {k: bool(v) for k, v in halt_rows[i].items() if k != "date"}

        # 1) 전일 결정한 목표를 오늘 시가에 체결
        if pending is not None:
            pv_exec = _portfolio_value(cash, shares, orow)
            cash, shares = _execute(pending, orow, hrow, cash, shares, pv_exec, cost_rate)
            pending = None

        # 2) 종가 기준 시가평가 기록
        equity.append((d, _portfolio_value(cash, shares, crow)))

        # 3) 리밸런싱 결정 (t 이하 데이터만 사용)
        if d in rebal:
            universe = members_asof(memberships, d)
            window = prices.filter((pl.col("date") <= d) & pl.col("symbol").is_in(list(universe)))
            scores = signal.generate(window)
            pending = optimize(scores, constraints, top_n=top_n)

    return _metrics(equity, risk_free=risk_free)


def run_backtest(config: AppConfig) -> dict[str, float]:
    """설정에 따라 백테스트를 실행하고 성과 지표를 반환한다.

    무비용 백테스트 금지: config.backtest.commission_bps / slippage_bps 반영.
    """
    log.info(
        "backtest start | env=%s seed=%s universe=%s",
        config.env,
        config.seed,
        config.data.universe,
    )
    memberships = load_universe(config.data.universe)
    prices = load_prices(config.data.universe, config.data.start_date, config.data.end_date)

    constraints = PortfolioConstraints(
        long_only=config.portfolio.long_only,
        market_neutral=config.portfolio.market_neutral,
        gross_exposure=config.portfolio.gross_exposure,
        max_weight=config.portfolio.max_weight,
    )
    metrics = simulate(
        prices,
        memberships,
        signal=Momentum(),
        constraints=constraints,
        initial_capital=config.backtest.initial_capital,
        commission_bps=config.backtest.commission_bps,
        slippage_bps=config.backtest.slippage_bps,
        top_n=config.portfolio.top_n,
    )
    log.info(
        "backtest done | CAGR=%.2f%% vol=%.2f%% Sharpe=%.2f MDD=%.2f%% days=%d",
        metrics["cagr"] * 100,
        metrics["vol"] * 100,
        metrics["sharpe"],
        metrics["mdd"] * 100,
        int(metrics["n_days"]),
    )
    return metrics
