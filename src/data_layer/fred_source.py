"""FRED(미 세인트루이스 연준) 기반 금리 소스. FDR 의 FRED 리더를 쓴다 — API 키 불필요.

기본 시리즈는 한국 3개월 은행간 금리(IR3TIB01KRM156N, 연율 %, 월별) — 국내 무위험금리 proxy.
다른 시리즈도 코드만 바꾸면 된다(예: IRLTLT01KRM156N 장기국채, DGS3MO 미 3개월 T-bill).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import polars as pl

# (series, start, end) -> date/rate 프레임. 테스트에서 주입해 모킹.
RateReadFn = Callable[[str, date, date], pl.DataFrame]

# 한국 3개월 은행간 금리 (연율 %). 국내 무위험금리 기본값.
DEFAULT_RISK_FREE_SERIES = "IR3TIB01KRM156N"


def _fred_rate(series: str, start: date, end: date) -> pl.DataFrame:
    """FDR 로 FRED 금리 시리즈를 조회해 date/rate 프레임으로 반환한다 (네트워크 격리)."""
    import FinanceDataReader as fdr  # 지연 import: 선택 의존성('data' extra)

    pdf = fdr.DataReader(f"FRED:{series}", start.isoformat(), end.isoformat())
    if pdf.empty:
        return pl.DataFrame(schema={"date": pl.Date(), "rate": pl.Float64()})
    frame = pl.from_pandas(pdf.reset_index())
    # reset_index 의 첫 컬럼이 날짜, 나머지 한 컬럼이 금리 값(컬럼명은 시리즈 코드).
    date_col = frame.columns[0]
    value_col = next(c for c in frame.columns if c != date_col)
    return (
        frame.rename({date_col: "date", value_col: "rate"})
        .with_columns(pl.col("date").cast(pl.Date))
        .select(["date", "rate"])
    )


@dataclass
class FredRateSource:
    """FRED 금리 소스. 기본은 한국 3개월 은행간 금리(무위험 proxy).

    Attributes:
        series: FRED 시리즈 코드.
        read_fn: 조회 함수. None 이면 FDR 실호출. 테스트에서 주입해 모킹.
    """

    series: str = DEFAULT_RISK_FREE_SERIES
    read_fn: RateReadFn | None = None

    def fetch(self, start: date, end: date) -> pl.DataFrame:
        fn = self.read_fn or _fred_rate
        return fn(self.series, start, end)
