"""전략 결합/분산. 여러 알파를 전략 단위 비중으로 합쳐 하나의 목표 점수를 만든다.

영상의 1번 원칙(다각화는 종목이 아니라 전략으로)을 코드로 옮긴 자리.
상충/보완되는 전략을 배분(allocation) 비중으로 묶는다. 향후 상관·리스크 패리티 기반
동적 배분으로 확장할 수 있다.
"""

from __future__ import annotations

from research.signals import SignalScores


def combine_scores(
    strategy_scores: dict[str, SignalScores],
    allocations: dict[str, float],
) -> SignalScores:
    """전략별 시그널 점수를 배분 비중으로 가중 결합한다.

    allocations 는 내부에서 합이 1이 되도록 정규화된다. 특정 전략에 점수가 없는
    자산은 0으로 본다. 결과는 자산별 결합 점수.

    Raises:
        ValueError: 배분 비중이 비었거나 합이 0이거나 음수가 섞인 경우,
            또는 배분에 없는 전략 점수가 들어온 경우.
    """
    if not allocations:
        raise ValueError("allocations 가 비어 있습니다 — 결합할 전략이 없습니다.")
    if any(w < 0 for w in allocations.values()):
        raise ValueError("배분 비중은 음수일 수 없습니다.")
    total = sum(allocations.values())
    if total <= 0:
        raise ValueError("배분 비중의 합이 0보다 커야 합니다.")
    unknown = set(strategy_scores) - set(allocations)
    if unknown:
        raise ValueError(f"배분 비중이 없는 전략 점수가 있습니다: {sorted(unknown)}")

    combined: SignalScores = {}
    for strategy, weight in allocations.items():
        norm = weight / total
        for asset, score in strategy_scores.get(strategy, {}).items():
            combined[asset] = combined.get(asset, 0.0) + norm * score
    return combined
