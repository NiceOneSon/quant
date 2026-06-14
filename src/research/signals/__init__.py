"""개별 알파(시그널) 모듈들.

영상의 1번 원칙: "절대 단일 전략을 쓰지 않는다. 다각화는 종목이 아니라 전략으로 한다."
각 시그널은 독립적인 알파를 산출하는 1급 단위이며, research.combine 에서 전략 단위로
분산·결합된다. 여기 한 파일 = 한 전략이 원칙.

모든 시그널은 `Signal` 프로토콜을 따른다. point-in-time 규칙은 시그널 내부에서도 유효:
generate(prices) 는 각 시점 t 의 점수를 낼 때 t 이후 데이터를 절대 참조하면 안 된다.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import polars as pl

# 자산별 점수(높을수록 매수 선호). 양수=롱, 음수=숏 선호(숏 확장 시).
SignalScores = dict[str, float]


@runtime_checkable
class Signal(Protocol):
    """개별 알파 전략의 공통 인터페이스."""

    name: str

    def generate(self, prices: pl.DataFrame) -> SignalScores:
        """가격 데이터(PRICE_SCHEMA long)로부터 자산별 시그널 점수를 산출한다.

        엔진이 prices 를 시점 t 이하·현재 유니버스로 미리 필터해 넘긴다.
        룩어헤드 금지: 넘어온 데이터(<= t)만 쓴다. 전체 기간 정규화 금지 — 롤링/확장만.
        """
        ...
