"""유니버스 멤버십 데이터 소스(수집 어댑터).

소스는 플러그인 가능한 Protocol 이다. 우선 파일 기반 CsvUniverseSource 로 파이프라인을
end-to-end 동작·테스트할 수 있게 한다. 실제 벤더(예: pykrx, 데이터 API)는 같은 Protocol 을
구현해 끼우면 된다 — 네트워크 호출 코드는 그 어댑터 안에만 둔다(테스트에서는 모킹).

⚠️ 어떤 소스든 편출·상장폐지 이력을 포함한 시점 정확 데이터를 내야 한다.
현재 구성종목만 담긴 스냅샷을 쓰면 생존편향이 들어간다.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol, runtime_checkable

import polars as pl

from data_layer.universe import Membership


@runtime_checkable
class UniverseSource(Protocol):
    """이름으로 멤버십 구간 목록을 가져오는 수집 소스."""

    def fetch(self, name: str) -> list[Membership]:
        """`name` 유니버스의 (편입일, 편출일) 멤버십 레코드를 반환한다."""
        ...


@runtime_checkable
class PriceSource(Protocol):
    """종목·기간으로 OHLCV 를 가져오는 수집 소스."""

    def fetch(self, ticker: str, start: date, end: date) -> pl.DataFrame:
        """한 종목의 [start, end] 일별 OHLCV 를 반환한다.

        컬럼: date, open, high, low, close(수정주가), volume, close_raw(원본 종가).
        symbol/is_halted 는 ingest 단계에서 붙인다.
        """
        ...


@runtime_checkable
class RateSource(Protocol):
    """기간으로 금리 시리즈를 가져오는 수집 소스."""

    def fetch(self, start: date, end: date) -> pl.DataFrame:
        """[start, end] 금리를 반환한다. 컬럼: date, rate(연율 %)."""
        ...


@dataclass
class CsvUniverseSource:
    """raw CSV 에서 과거 멤버십 이력을 주입하는 소스 (수동 PIT 유니버스).

    과거 구간을 즉시 백테스트하려면 상장폐지·편출 종목을 포함한 시점 정확 멤버십을 이 CSV 로
    주입한다. FDR 스냅샷 누적이 *앞으로만* 쌓이는 것과 달리, 이건 *과거* 이력을 직접 채운다.

    CSV 형식: 헤더 `symbol,added,removed`. 날짜는 ISO(YYYY-MM-DD). 한 행 = 한 편입 구간
    [added, removed). `removed` 가 비어 있으면 아직 편입 유지(null). 한 종목이 편출 후 재편입
    했다면 행을 여러 개 둔다(구간이 겹치면 안 됨 — ingest 의 normalize 가 거부).
    파일 경로: `<raw_dir>/<name>.csv` (CLI 기본: data/raw/universe/<universe>.csv).

    예)
        symbol,added,removed
        005930,2010-01-01,
        068270,2010-01-01,2018-06-01
        068270,2020-03-01,
    """

    raw_dir: Path

    def fetch(self, name: str) -> list[Membership]:
        path = self.raw_dir / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"raw 유니버스 CSV 가 없습니다: {path}")
        memberships: list[Membership] = []
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                removed = (row.get("removed") or "").strip()
                memberships.append(
                    Membership(
                        symbol=row["symbol"].strip(),
                        added=date.fromisoformat(row["added"].strip()),
                        removed=date.fromisoformat(removed) if removed else None,
                    )
                )
        return memberships
