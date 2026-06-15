"""EIA (U.S. Energy Information Administration) 원자재 시계열 소스.

FRED 경유(DCOILWTICO)보다 1~3일 빠른 WTI/Brent 스팟 가격 직접 조회.
API 키 무료 발급: https://www.eia.gov/opendata/
환경변수: EIA_API_KEY
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import polars as pl

# EIA 스팟 가격 시리즈 코드
EIA_WTI = "RWTC"     # Cushing, OK WTI Spot Price ($/bbl)
EIA_BRENT = "RBRTE"  # Europe Brent Spot Price ($/bbl)

_ENDPOINT = "https://api.eia.gov/v2/petroleum/pri/spt/data/"
_PAGE = 5000

# (series, start, end) -> date/value 프레임. 테스트에서 주입.
EiaReadFn = Callable[[str, date, date], pl.DataFrame]


def _eia_fetch(series: str, start: date, end: date) -> pl.DataFrame:
    """EIA API v2 로 series 를 조회한다 (네트워크 격리 — 테스트에서는 주입)."""
    api_key = os.environ.get("EIA_API_KEY", "")
    if not api_key:
        raise OSError("EIA_API_KEY 환경변수가 설정되지 않았습니다.")

    import httpx  # 지연 import: 선택 의존성('data' extra)

    rows: list[dict[str, object]] = []
    offset = 0
    while True:
        params: dict[str, object] = {
            "api_key": api_key,
            "data[0]": "value",
            "facets[series][]": series,
            "frequency": "daily",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": _PAGE,
            "offset": offset,
        }
        resp = httpx.get(_ENDPOINT, params=params, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        batch: list[dict[str, object]] = body.get("response", {}).get("data", [])
        rows.extend(batch)
        total = int(body.get("response", {}).get("total", 0))
        offset += len(batch)
        if not batch or offset >= total:
            break
        time.sleep(0.3)  # 페이지네이션 throttle

    if not rows:
        return pl.DataFrame(schema={"date": pl.Date(), "value": pl.Float64()})

    # EIA 는 value=None(결측) 행을 포함할 수 있음 → 드롭.
    valid = [r for r in rows if r.get("value") is not None]
    if not valid:
        return pl.DataFrame(schema={"date": pl.Date(), "value": pl.Float64()})

    return (
        pl.DataFrame(
            {"date": [r["period"] for r in valid], "value": [r["value"] for r in valid]}
        )
        .with_columns(pl.col("date").str.to_date())
        .with_columns(pl.col("value").cast(pl.Float64))
    )


@dataclass
class EiaSeriesSource:
    """EIA API v2 원자재 스팟 가격 소스. MacroSource 프로토콜 구현.

    FRED/DCOILWTICO 대비 1~3일 빠른 WTI/Brent 스팟 가격을 제공한다.
    환경변수 EIA_API_KEY 필요 (무료: https://www.eia.gov/opendata/).

    Attributes:
        series: EIA 시리즈 코드. EIA_WTI("RWTC") 또는 EIA_BRENT("RBRTE").
        read_fn: 조회 함수. None 이면 실호출. 테스트에서 주입해 모킹.
    """

    series: str = EIA_WTI
    read_fn: EiaReadFn | None = None

    def fetch(self, start: date, end: date) -> pl.DataFrame:
        """[start, end] 스팟 가격을 반환한다. 컬럼: date, value($/bbl)."""
        fn = self.read_fn or _eia_fetch
        return fn(self.series, start, end)
