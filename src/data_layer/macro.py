"""매크로/FX/원자재/지수 시계열 저장·조회.

수집(ingest)은 data_layer.ingest 로 격리한다. 여기는 경로·조회만 담당한다.
소비 레이어는 dbt 마트(fct_macro)를 읽는다 → 먼저 `dbt build`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from data_layer.universe import DEFAULT_DATA_DIR, default_marts_dir


def _parse(d: str | date) -> date:
    return d if isinstance(d, date) else date.fromisoformat(d)


def load_macro(
    series: str,
    start: str | date | None = None,
    end: str | date | None = None,
    *,
    marts_dir: Path | None = None,
) -> pl.DataFrame:
    """dbt 마트(fct_macro)에서 `series` 시계열을 조회한다.

    컬럼: date, series, label, unit, country, category, value.
    start/end 로 날짜 구간 필터.
    """
    path = (marts_dir or default_marts_dir()) / "fct_macro.parquet"
    if not path.exists():
        raise FileNotFoundError(f"마트가 없습니다: {path} — dbt build 로 생성하세요(dbt/).")
    df = pl.read_parquet(path).filter(pl.col("series") == series)
    if start is not None:
        df = df.filter(pl.col("date") >= _parse(start))
    if end is not None:
        df = df.filter(pl.col("date") <= _parse(end))
    return df
