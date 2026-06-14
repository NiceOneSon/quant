"""환경별 설정 로딩. 설정은 코드에 하드코딩하지 않고 YAML + 환경변수로 주입한다."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel

CONFIGS_DIR = Path(__file__).resolve().parents[2] / "configs"


class DataConfig(BaseModel):
    universe: str = "default"
    start_date: str
    end_date: str


class DcaConfig(BaseModel):
    # 정액적립식(Dollar-Cost Averaging) 시나리오 — 개인 투자자용 백테스트.
    # 영상 후반: 개인은 마켓 타이밍 대신 DCA 가 적합.
    enabled: bool = False
    amount: float = 0.0  # 매 적립 시 투입 금액
    interval_days: int = 30  # 적립 주기(일)


class BacktestConfig(BaseModel):
    initial_capital: float = 1_000_000.0
    # 무비용 백테스트 금지 — 거래비용은 항상 명시한다
    commission_bps: float = 5.0
    slippage_bps: float = 2.0
    dca: DcaConfig = DcaConfig()


class PortfolioConfig(BaseModel):
    # 개인용 기본은 롱온리. 숏/시장중립은 추후 플래그로만 활성화(optimizer 와 일치).
    long_only: bool = True
    market_neutral: bool = False
    gross_exposure: float = 1.0
    max_weight: float = 0.1
    top_n: int = 20  # 동일가중으로 담을 상위 종목 수


class AppConfig(BaseModel):
    env: str = "dev"
    # 기본은 안전: 실거래는 명시적으로 켜야 한다
    live_trading: bool = False
    seed: int = 42
    data: DataConfig
    backtest: BacktestConfig
    portfolio: PortfolioConfig = PortfolioConfig()


def load_config(name: str) -> AppConfig:
    """configs/<name>.yaml 을 읽어 검증된 설정 객체로 반환한다."""
    path = CONFIGS_DIR / f"{name}.yaml"
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    cfg = AppConfig.model_validate(raw)
    # 환경변수가 우선
    cfg.env = os.environ.get("ENV", cfg.env)
    return cfg
