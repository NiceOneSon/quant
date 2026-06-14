"""사전 리스크 체크. 모든 라이브 집행은 이 체크를 통과해야 한다."""

from __future__ import annotations


def pretrade_check(orders: object, *, live: bool) -> bool:
    """포지션·노출 한도, 킬 스위치 등을 검증한다.

    live=True 인데 검증을 통과하지 못하면 주문을 막아야 한다.
    """
    raise NotImplementedError
