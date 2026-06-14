"""무위험금리(risk-free rate) 저장·조회. Sharpe·초과수익 계산의 기준값.

저장 포맷: date, rate(연율 %). 소스에 따라 빈도가 다를 수 있다(예: FRED 한국 3개월
은행간 금리는 월별). 백테스트는 필요 시 영업일로 forward-fill 하고 일율로 환산해 쓴다.

수집(ingest)은 data_layer.ingest 로 격리한다. 여기는 스키마·경로·조회만 담당한다.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from data_layer.universe import DEFAULT_DATA_DIR, default_marts_dir

# Python 이 raw parquet 으로 저장하는 스키마(country 없음).
# country 는 dbt int_rates_enriched 에서 rate_series seed 조인으로 파생 → ELT 패턴.
RAW_RATE_SCHEMA: dict[str, pl.DataType] = {
    "date": pl.Date(),
    "series": pl.String(),
    "rate": pl.Float64(),
}

# 소비 레이어(dbt mart)의 스키마 — label·tenor 는 dbt 에서 추가됨.
RATE_SCHEMA: dict[str, pl.DataType] = {
    "date": pl.Date(),
    "series": pl.String(),
    "country": pl.String(),
    "rate": pl.Float64(),
}

# 금리 시리즈 메타 — (국가, 라벨). 새 시리즈는 여기 등록한다(미등록 시 country='NA').
RATE_SERIES: dict[str, tuple[str, str]] = {
    "IR3TIB01KRM156N": ("KR", "한국 3개월 은행간"),
    "DGS3MO": ("US", "미국채 3개월"),
    "DGS2": ("US", "미국채 2년"),
    "DGS10": ("US", "미국채 10년"),
    "DFF": ("US", "미 연방기금금리"),
}


def series_country(series: str) -> str:
    """시리즈 코드의 국가 구분을 반환한다(미등록은 'NA')."""
    return RATE_SERIES.get(series, ("NA", series))[0]


def _parse(d: str | date) -> date:
    return d if isinstance(d, date) else date.fromisoformat(d)


def rates_path(series: str, data_dir: Path | None = None) -> Path:
    """`series` 금리 데이터의 parquet 경로를 반환한다."""
    return (data_dir or DEFAULT_DATA_DIR) / "reference" / "rates" / f"{series}.parquet"


def load_rates(
    series: str,
    start: str | date | None = None,
    end: str | date | None = None,
    *,
    marts_dir: Path | None = None,
) -> pl.DataFrame:
    """dbt 마트에서 `series` 금리를 조회한다 (date, series, country, label, tenor, rate).

    fct_rates(SK + rate) JOIN dim_rate_series(메타) → series 필터.
    start/end 로 구간 필터.
    """
    d = marts_dir or default_marts_dir()
    fct_path = d / "fct_rates.parquet"
    dim_path = d / "dim_rate_series.parquet"
    for p in (fct_path, dim_path):
        if not p.exists():
            raise FileNotFoundError(f"마트가 없습니다: {p} — dbt build 로 생성하세요(dbt/).")
    fct = pl.read_parquet(fct_path)
    dim = pl.read_parquet(dim_path)
    df = (
        fct.join(dim, left_on="sk_dim_rate_series", right_on="sk_id")
        .filter(pl.col("series") == series)
    )
    if start is not None:
        df = df.filter(pl.col("date") >= _parse(start))
    if end is not None:
        df = df.filter(pl.col("date") <= _parse(end))
    return df
