"""Point-in-time 유니버스 멤버십. 생존편향(survivorship bias)을 구조적으로 막는다.

핵심 규칙(영상에서 가장 길게 강조한 함정):
- 백테스트는 "오늘의 구성종목"이 아니라 "그 시점의 구성종목"으로 돌려야 한다.
- 상장폐지·합병·편출된 종목도 그 시점에 편입돼 있었다면 유니버스에 포함돼야 한다.
- 따라서 멤버십은 (편입일, 편출일) 구간으로 저장하고, 특정 날짜 기준으로 조회한다.
  "현재 살아있는 종목만" 필터링하는 코드는 생존편향을 만든다 — 절대 금지.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import polars as pl

# 저장소 규약: point-in-time 멤버십은 reference 데이터로 parquet 에 보관한다.
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "data"


def default_marts_dir() -> Path:
    """dbt 마트 출력 디렉터리. QUANT_MARTS_DIR 환경변수 우선(없으면 data/marts)."""
    env = os.environ.get("QUANT_MARTS_DIR")
    return Path(env) if env else DEFAULT_DATA_DIR / "marts"


# 저장 스키마 — removed 는 null 허용(아직 편입 유지).
_SCHEMA: dict[str, pl.DataType] = {
    "symbol": pl.String(),
    "added": pl.Date(),
    "removed": pl.Date(),
}


def _parse(d: str | date) -> date:
    return d if isinstance(d, date) else date.fromisoformat(d)


@dataclass(frozen=True)
class Membership:
    """한 종목의 유니버스 편입 구간 (반개구간 [added, removed))."""

    symbol: str
    added: date
    removed: date | None = None  # None 이면 아직 편입 유지(또는 데이터 끝까지)

    def active_on(self, asof: date) -> bool:
        if asof < self.added:
            return False
        return self.removed is None or asof < self.removed


def members_asof(memberships: list[Membership], asof: str | date) -> set[str]:
    """`asof` 시점에 유니버스에 편입돼 있던 종목 집합을 반환한다.

    이후에 상장폐지·편출된 종목이라도 `asof` 시점에 편입돼 있었다면 포함된다
    (생존편향 방지). 호출자는 이 결과만으로 그 시점의 의사결정을 내려야 한다.
    """
    on = _parse(asof)
    return {m.symbol for m in memberships if m.active_on(on)}


def snapshots_to_memberships(
    snapshots: list[tuple[date, set[str]]],
) -> list[Membership]:
    """시간순 구성종목 스냅샷들을 (편입, 편출) 멤버십 구간으로 복원한다 (순수).

    연속으로 등장한 구간을 하나의 멤버십으로 본다. 사라졌다 재등장하면 별도 구간이 된다
    (재편입). removed 는 처음으로 부재가 관측된 스냅샷 날짜로 둔다(반개구간 [added, removed)
    이므로 그 날부터 비편입으로 취급 — 보수적). 결과는 (symbol, added) 기준 정렬(재현성).

    주의: 누적 관측 기반이라 added 는 "처음 관측된 시점"이다. 첫 스냅샷 이전의 편입 이력은
    알 수 없다(과거 백필 불가). 편출은 관측 시작 이후 빠진 종목만 잡힌다.
    """
    open_added: dict[str, date] = {}
    result: list[Membership] = []
    for snap_date, members in snapshots:
        # 이번 스냅샷에서 사라진 종목 → 구간 종료
        for symbol in list(open_added):
            if symbol not in members:
                result.append(Membership(symbol, added=open_added[symbol], removed=snap_date))
                del open_added[symbol]
        # 새로 등장한 종목 → 구간 시작
        for symbol in members:
            if symbol not in open_added:
                open_added[symbol] = snap_date
    # 끝까지 편입 유지 중인 종목
    for symbol, added in open_added.items():
        result.append(Membership(symbol, added=added, removed=None))
    return sorted(result, key=lambda m: (m.symbol, m.added))


def universe_path(name: str, data_dir: Path | None = None) -> Path:
    """`name` 유니버스의 멤버십 parquet 경로를 반환한다."""
    return (data_dir or DEFAULT_DATA_DIR) / "reference" / "universe" / f"{name}.parquet"


def memberships_to_frame(memberships: list[Membership]) -> pl.DataFrame:
    """멤버십 리스트를 저장용 polars 프레임으로 변환한다 (순수 변환)."""
    return pl.DataFrame(
        {
            "symbol": [m.symbol for m in memberships],
            "added": [m.added for m in memberships],
            "removed": [m.removed for m in memberships],
        },
        schema=_SCHEMA,
    )


def frame_to_memberships(df: pl.DataFrame) -> list[Membership]:
    """저장 프레임을 멤버십 리스트로 복원한다 (순수 변환)."""
    return [
        Membership(symbol=row["symbol"], added=row["added"], removed=row["removed"])
        for row in df.to_dicts()
    ]


def load_universe(name: str, *, marts_dir: Path | None = None) -> list[Membership]:
    """dbt 마트(dim_universe)에서 `name` 유니버스의 point-in-time 멤버십을 로드한다.

    소비 레이어는 raw 가 아니라 dbt 마트를 읽는다 → 먼저 `dbt build` 로 마트를 생성해야 한다.
    편출·상장폐지 이력을 포함하므로(생존편향 방지) members_asof 로 그 시점 구성종목을 조회한다.
    (수집 파이프라인 내부에서 raw 멤버십이 필요하면 universe_path 로 직접 읽는다.)
    """
    path = (marts_dir or default_marts_dir()) / "dim_universe.parquet"
    if not path.exists():
        raise FileNotFoundError(f"마트가 없습니다: {path} — dbt build 로 생성하세요(dbt/).")
    df = pl.read_parquet(path).filter(pl.col("universe") == name)
    return frame_to_memberships(df)
