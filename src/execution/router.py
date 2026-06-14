"""주문 집행. 기본은 dry-run/paper. 실거래는 명시적 플래그로만 활성화."""

from __future__ import annotations


def submit(orders: object, *, live: bool = False) -> object:
    if live:
        raise RuntimeError("라이브 집행은 명시적 확인과 사전 리스크 체크 후에만 허용됩니다.")
    raise NotImplementedError
