"""포트폴리오 최적화. 기대수익·리스크·제약을 받아 목표 포지션을 산출한다.

개인용 기본은 롱온리(long_only=True). 단, 롱숏/시장중립을 1급 제약으로 노출해 두어
나중에 숏을 켜는 것이 플래그 변경만으로 가능하도록 설계한다(영상의 4번: 롱숏/시장중립이
하락장에서 강한 전략의 근간).
"""

from __future__ import annotations

from dataclasses import dataclass

from research.signals import SignalScores


@dataclass(frozen=True)
class PortfolioConstraints:
    """포지션 산출 제약.

    Attributes:
        long_only: 숏 금지(개인용 기본). False 로 두면 숏 허용.
        market_neutral: 순노출(net exposure) 0 을 목표(달러 중립). 숏이 필요하므로
            long_only 와 동시에 켤 수 없다.
        gross_exposure: 총노출 |long| + |short| 한도(자본 대비 배수).
        beta_target: 목표 시장 베타. 0 이면 베타 중립. None 이면 제약 없음.
        max_weight: 종목당 최대 비중(절댓값).
    """

    long_only: bool = True
    market_neutral: bool = False
    gross_exposure: float = 1.0
    beta_target: float | None = None
    max_weight: float = 0.1

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.long_only and self.market_neutral:
            raise ValueError("market_neutral 은 숏이 필요하므로 long_only 와 함께 켤 수 없습니다.")
        if self.gross_exposure <= 0:
            raise ValueError("gross_exposure 는 양수여야 합니다.")
        if not 0 < self.max_weight <= 1:
            raise ValueError("max_weight 는 (0, 1] 범위여야 합니다.")


def optimize(
    scores: SignalScores,
    constraints: PortfolioConstraints | None = None,
    *,
    top_n: int = 20,
) -> dict[str, float]:
    """결합 시그널 점수와 제약으로부터 목표 비중을 산출한다.

    백테스트 슬라이스 구현: 점수 상위 `top_n` 종목을 동일가중 롱온리로 담는다(양수 점수만).
    각 비중은 gross_exposure/n 이며 max_weight 로 캡한다(캡되면 나머지는 현금).

    숏/시장중립(long_only=False)은 아직 미구현 — 추후 평균분산·시장중립 최적화로 확장.
    """
    cons = constraints or PortfolioConstraints()
    cons.validate()
    if not cons.long_only:
        raise NotImplementedError("숏/시장중립 최적화는 아직 미구현입니다(슬라이스 범위 밖).")

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    picks = [sym for sym, score in ranked if score > 0][:top_n]
    if not picks:
        return {}
    weight = min(cons.gross_exposure / len(picks), cons.max_weight)
    return {sym: weight for sym in picks}
