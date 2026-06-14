"""매크로/FX/원자재/지수 시계열 저장·조회.

수집(ingest)은 data_layer.ingest 로 격리한다. 여기는 경로·조회만 담당한다.
소비 레이어는 dbt 마트(fct_macro JOIN dim_macro_series)를 읽는다 → 먼저 `dbt build`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from data_layer.universe import default_marts_dir


def _parse(d: str | date) -> date:
    return d if isinstance(d, date) else date.fromisoformat(d)


def load_macro(
    series: str,
    start: str | date | None = None,
    end: str | date | None = None,
    *,
    marts_dir: Path | None = None,
) -> pl.DataFrame:
    """dbt 마트에서 `series` 시계열을 조회한다 (date, series, label, unit, country, category, value).

    fct_macro(SK + 측정값) JOIN dim_macro_series(메타) → series 필터.
    start/end 로 날짜 구간 필터.
    """
    d = marts_dir or default_marts_dir()
    fct_path = d / "fct_macro.parquet"
    dim_path = d / "dim_macro_series.parquet"
    for p in (fct_path, dim_path):
        if not p.exists():
            raise FileNotFoundError(f"마트가 없습니다: {p} — dbt build 로 생성하세요(dbt/).")
    fct = pl.read_parquet(fct_path)
    dim = pl.read_parquet(dim_path)
    df = (
        fct.join(dim, left_on="sk_dim_macro_series", right_on="sk_id")
        .filter(pl.col("series") == series)
    )
    if start is not None:
        df = df.filter(pl.col("date") >= _parse(start))
    if end is not None:
        df = df.filter(pl.col("date") <= _parse(end))
    return df
