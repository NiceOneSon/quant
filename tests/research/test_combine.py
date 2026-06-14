import pytest

from research.combine import combine_scores


def test_allocations_normalized_and_weighted() -> None:
    scores = {
        "mom": {"AAA": 1.0, "BBB": 0.0},
        "rev": {"AAA": -1.0, "BBB": 2.0},
    }
    # 비중 3:1 -> 정규화 0.75:0.25
    out = combine_scores(scores, {"mom": 3.0, "rev": 1.0})
    assert out["AAA"] == pytest.approx(0.75 * 1.0 + 0.25 * -1.0)
    assert out["BBB"] == pytest.approx(0.75 * 0.0 + 0.25 * 2.0)


def test_missing_allocation_rejected() -> None:
    with pytest.raises(ValueError):
        combine_scores({"mom": {"AAA": 1.0}}, {"rev": 1.0})


def test_zero_allocation_sum_rejected() -> None:
    with pytest.raises(ValueError):
        combine_scores({"mom": {"AAA": 1.0}}, {"mom": 0.0})
