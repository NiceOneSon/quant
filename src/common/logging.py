"""구조화 로깅. 코드 전반에서 print() 대신 이 로거를 사용한다."""

from __future__ import annotations

import logging

_CONFIGURED = False


def get_logger(name: str) -> logging.Logger:
    global _CONFIGURED
    if not _CONFIGURED:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        )
        _CONFIGURED = True
    return logging.getLogger(name)
