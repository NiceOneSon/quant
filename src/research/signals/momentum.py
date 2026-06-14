"""횡단면 모멘텀 알파. signals 패키지의 작성 패턴 예시 + 백테스트 슬라이스용 실구현.

새 전략은 이 파일을 본떠 한 파일 = 한 전략으로 추가하고, research.combine 에서 결합한다.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from research.signals import SignalScores


@dataclass
class Momentum:
    """과거 `lookback` 거래일 수익률 기반 횡단면 모멘텀(최근 `skip` 일 제외)."""

    lookback: int = 126  # 약 6개월(거래일)
    skip: int = 21  # 최근 1개월 단기 반전 제거
    name: str = "momentum"

    def generate(self, prices: pl.DataFrame) -> SignalScores:
        """[t-skip-lookback, t-skip] 구간 수익률을 종목별 점수로 낸다.

        prices 는 엔진이 t 이하·유니버스로 필터해 넘긴 long 프레임(date, symbol, close).
        룩어헤드 금지: 넘어온 close(<= t)만 쓰고, 최근 skip 일은 제외한다.
        충분한 이력(lookback+skip+1 봉)이 없는 종목은 점수를 내지 않는다.
        """
        need = self.lookback + self.skip + 1
        scores: SignalScores = {}
        ordered = prices.sort(["symbol", "date"])
        for key, group in ordered.group_by("symbol", maintain_order=True):
            closes = group["close"].to_list()
            if len(closes) < need:
                continue
            recent = closes[-1 - self.skip]
            past = closes[-1 - self.skip - self.lookback]
            if past is None or recent is None or past <= 0:
                continue
            symbol = key[0]
            scores[str(symbol)] = recent / past - 1.0
        return scores
