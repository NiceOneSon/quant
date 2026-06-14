"""한국은행 ECOS API 기반 매크로 시계열 소스.

시리즈 코드 형식: "STAT_CODE:ITEM_CODE:CYCLE"
  예) "151Y002:BBMA00:MM"  → M2 광의통화 (월별)
      "722Y001:0101000:MM" → 한국은행 기준금리 (월별)

ECOS throttle 정책: 3분간 300회 초과 시 30분 차단(ERROR-602).
→ 호출 간 최소 1초 sleep 필수.

환경변수: ECOS_KEY (ecos.bok.or.kr 발급 무료 키)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import date

import polars as pl


_ECOS_BASE = "https://ecos.bok.or.kr/api/StatisticSearch"
_MIN_INTERVAL = 1.1  # 초. ECOS rate limit 방어용.
_last_call: float = 0.0


def _ecos_key() -> str:
    key = os.environ.get("ECOS_KEY", "")
    if not key:
        raise RuntimeError("ECOS_KEY 환경변수가 설정되지 않았습니다.")
    return key


def _format_period(d: date, cycle: str) -> str:
    """날짜 → ECOS period 문자열 (MM: YYYYMM, DD: YYYYMMDD)."""
    if cycle == "MM":
        return d.strftime("%Y%m")
    return d.strftime("%Y%m%d")


def _parse_period(time_str: str, cycle: str) -> date:
    """ECOS TIME 문자열 → date (월별: 1일, 일별: 당일)."""
    if cycle == "MM":
        return date(int(time_str[:4]), int(time_str[4:6]), 1)
    return date(int(time_str[:4]), int(time_str[4:6]), int(time_str[6:8]))


def _throttle() -> None:
    global _last_call
    elapsed = time.monotonic() - _last_call
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call = time.monotonic()


def _fetch_ecos(
    stat_code: str,
    item_code: str,
    cycle: str,
    start: date,
    end: date,
) -> pl.DataFrame:
    """ECOS StatisticSearch API 호출 → date/value DataFrame."""
    import urllib.request
    import json

    key = _ecos_key()
    start_p = _format_period(start, cycle)
    end_p = _format_period(end, cycle)
    url = (
        f"{_ECOS_BASE}/{key}/json/kr/1/10000"
        f"/{stat_code}/{cycle}/{start_p}/{end_p}/{item_code}"
    )

    _throttle()
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    # 오류 응답 처리
    if "RESULT" in data:
        code = data["RESULT"].get("CODE", "")
        msg = data["RESULT"].get("MESSAGE", "")
        if code == "INFO-200":
            return pl.DataFrame(schema={"date": pl.Date(), "value": pl.Float64()})
        raise RuntimeError(f"ECOS API 오류 {code}: {msg}")

    rows = data.get("StatisticSearch", {}).get("row", [])
    if not rows:
        return pl.DataFrame(schema={"date": pl.Date(), "value": pl.Float64()})

    records = [
        {
            "date": _parse_period(r["TIME"], cycle),
            "value": float(r["DATA_VALUE"]) if r["DATA_VALUE"] else None,
        }
        for r in rows
        if r.get("DATA_VALUE") not in (None, "", " ")
    ]
    return pl.DataFrame(records, schema={"date": pl.Date(), "value": pl.Float64()})


@dataclass
class EcosSeriesSource:
    """ECOS API 매크로 시계열 소스.

    Attributes:
        series: "STAT_CODE:ITEM_CODE:CYCLE" 형식 시리즈 코드.
                예) "151Y002:BBMA00:MM"
    """

    series: str

    def fetch(self, start: date, end: date) -> pl.DataFrame:
        parts = self.series.split(":")
        if len(parts) != 3:
            raise ValueError(
                f"ECOS series 형식 오류: '{self.series}' — 'STAT_CODE:ITEM_CODE:CYCLE' 필요"
            )
        stat_code, item_code, cycle = parts
        return _fetch_ecos(stat_code, item_code, cycle, start, end)
