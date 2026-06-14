"""가격 데이터 저장·조회. point-in-time 정확성을 보장한다 (미래 정보 누출 금지).

저장 포맷(long): 한 행 = (날짜, 종목)의 OHLCV.
- open/high/low/close/volume 은 **수정주가(adjusted)** 기준 — 백테스트가 직접 쓰는 값.
- close_raw 는 원본(미수정) 종가 — 수정계수(close/close_raw)를 복원하기 위해 함께 보관.
  ⚠️ 벤더에 따라 비어 올 수 있어 nullable 이다(예: pykrx 1.0.51 은 adjusted=False 가 빈
  프레임 → close_raw=null). null 이면 수정계수 복원 불가.
- is_halted 는 거래정지/무거래(거래량 0) 표시 — 백테스트는 이 날 체결 가능으로 보면 안 된다.

수집(ingest)은 data_layer.ingest 로 격리한다. 여기는 스키마·경로·조회(읽기)만 담당한다.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from data_layer.universe import DEFAULT_DATA_DIR

# 저장 스키마. 컬럼 순서·타입의 단일 출처.
PRICE_SCHEMA: dict[str, pl.DataType] = {
    "date": pl.Date(),
    "symbol": pl.String(),
    "open": pl.Float64(),
    "high": pl.Float64(),
    "low": pl.Float64(),
    "close": pl.Float64(),  # 수정주가 종가
    "volume": pl.Int64(),
    "close_raw": pl.Float64(),  # 원본(미수정) 종가 — 수정계수 복원용
    "is_halted": pl.Boolean(),  # 거래정지/무거래
}


def _parse(d: str | date) -> date:
    return d if isinstance(d, date) else date.fromisoformat(d)


def prices_path(universe: str, data_dir: Path | None = None) -> Path:
    """`universe` 가격 데이터의 parquet 경로를 반환한다."""
    return (data_dir or DEFAULT_DATA_DIR) / "processed" / "prices" / f"{universe}.parquet"


def load_prices(
    universe: str,
    start: str | date | None = None,
    end: str | date | None = None,
    *,
    data_dir: Path | None = None,
) -> pl.DataFrame:
    """저장된 `universe` 가격 데이터를 조회한다 (수정주가 + 원본 + 거래정지 플래그).

    start/end 가 주어지면 해당 구간으로 필터한다. 반환 스키마는 PRICE_SCHEMA.
    파일이 없으면 먼저 `scripts/ingest.py --dataset prices` 로 수집해야 한다.
    """
    path = prices_path(universe, data_dir)
    if not path.exists():
        raise FileNotFoundError(f"가격 데이터 파일이 없습니다: {path} — 먼저 ingest 로 수집하세요.")
    df = pl.read_parquet(path)
    if start is not None:
        df = df.filter(pl.col("date") >= _parse(start))
    if end is not None:
        df = df.filter(pl.col("date") <= _parse(end))
    return df
