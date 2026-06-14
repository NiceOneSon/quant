import pytest

from portfolio.optimizer import PortfolioConstraints, optimize


def test_default_is_long_only() -> None:
    # 개인용 기본: 롱온리
    cons = PortfolioConstraints()
    assert cons.long_only is True
    assert cons.market_neutral is False


def test_long_only_and_market_neutral_conflict() -> None:
    # 시장중립은 숏이 필요하므로 롱온리와 동시 활성화 불가
    with pytest.raises(ValueError):
        PortfolioConstraints(long_only=True, market_neutral=True)


def test_short_enabled_market_neutral_is_valid() -> None:
    # 추후 숏 확장: long_only 를 끄면 시장중립 구성이 허용된다
    cons = PortfolioConstraints(long_only=False, market_neutral=True, beta_target=0.0)
    assert cons.market_neutral is True


def test_optimize_top_n_equal_weight() -> None:
    scores = {"A": 0.3, "B": 0.2, "C": 0.1, "D": -0.5}
    w = optimize(scores, PortfolioConstraints(max_weight=1.0), top_n=2)
    assert w == {"A": 0.5, "B": 0.5}  # 상위 2, 동일가중(gross 1.0)


def test_optimize_excludes_nonpositive_and_caps_weight() -> None:
    scores = {"A": 0.3, "B": -0.1}
    # 양수만 담고, max_weight 캡 적용(1.0/1=1.0 → 0.1 로 캡)
    w = optimize(scores, PortfolioConstraints(max_weight=0.1), top_n=5)
    assert w == {"A": 0.1}


def test_optimize_short_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        optimize({"A": 0.3}, PortfolioConstraints(long_only=False))
