from common.config import load_config


def test_backtest_config_loads_with_costs() -> None:
    cfg = load_config("backtest")
    # 무비용 백테스트가 기본이 되면 안 된다
    assert cfg.backtest.commission_bps > 0
    assert cfg.backtest.slippage_bps > 0


def test_live_trading_defaults_off() -> None:
    cfg = load_config("backtest")
    # 안전 기본값: 실거래는 꺼져 있어야 한다
    assert cfg.live_trading is False


def test_portfolio_defaults_long_only() -> None:
    cfg = load_config("backtest")
    # 개인용 기본: 롱온리, 숏/시장중립은 꺼져 있어야 한다
    assert cfg.portfolio.long_only is True
    assert cfg.portfolio.market_neutral is False


def test_dca_defaults_off() -> None:
    cfg = load_config("backtest")
    # DCA 시나리오는 명시적으로 켜야 한다
    assert cfg.backtest.dca.enabled is False
