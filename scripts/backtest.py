"""백테스트 실행 진입점.

사용법: uv run python scripts/backtest.py --config configs/backtest.yaml
"""

from __future__ import annotations

import argparse

from common.config import load_config
from common.logging import get_logger
from research.backtest import run_backtest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="설정 이름 또는 경로 (예: backtest)")
    args = parser.parse_args()

    name = args.config.split("/")[-1].replace(".yaml", "")
    config = load_config(name)
    metrics = run_backtest(config)
    log = get_logger(__name__)
    log.info("metrics | %s", {k: round(v, 4) for k, v in metrics.items()})


if __name__ == "__main__":
    main()
