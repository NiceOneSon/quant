"""스냅샷 누적 기반 point-in-time 유니버스.

FDR StockListing 같은 소스는 "현재 상장목록" 스냅샷만 준다. 이를 시점마다 반복 수집해
(asof, symbol) 로그로 누적하면, 스냅샷 차집합으로 멤버십 구간(편입/편출)을 복원할 수 있다
(snapshots_to_memberships). 이렇게 하면 관측 시작 이후의 상장폐지·편출이 반영돼 생존편향을
*앞으로* 제거한다.

한계(정직하게): 첫 스냅샷 이전 이력은 복원 불가(과거 백필 안 됨). 과거 PIT 유니버스가
필요하면 별도 historical 멤버십 소스로 universe_path 를 직접 채우거나(CsvUniverseSource),
스냅샷을 충분히 오래 누적해야 한다. 누적은 주기적으로(예: 매 거래일/매주) 실행한다.

저장:
- 스냅샷 로그: data/reference/universe_snapshots/<name>.parquet  (asof, symbol)
- 복원 결과:   data/reference/universe/<name>.parquet            (Membership; load_universe 가 읽음)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from data_layer.universe import (
    DEFAULT_DATA_DIR,
    memberships_to_frame,
    snapshots_to_memberships,
    universe_path,
)

SNAPSHOT_SCHEMA: dict[str, pl.DataType] = {
    "asof": pl.Date(),
    "symbol": pl.String(),
}


def snapshots_path(name: str, data_dir: Path | None = None) -> Path:
    """`name` 유니버스의 스냅샷 로그 parquet 경로."""
    return (data_dir or DEFAULT_DATA_DIR) / "reference" / "universe_snapshots" / f"{name}.parquet"


def record_snapshot(
    name: str,
    asof: date,
    symbols: list[str],
    *,
    data_dir: Path | None = None,
) -> int:
    """현재 스냅샷(asof 시점의 종목 집합)을 로그에 누적한다. 같은 asof 는 교체(멱등).

    Returns:
        누적된 총 스냅샷(고유 asof) 개수.
    """
    new = pl.DataFrame(
        {"asof": [asof] * len(symbols), "symbol": sorted(set(symbols))},
        schema=SNAPSHOT_SCHEMA,
    )
    path = snapshots_path(name, data_dir)
    if path.exists():
        existing = pl.read_parquet(path).filter(pl.col("asof") != asof)
        combined = pl.concat([existing, new])
    else:
        combined = new
    combined = combined.sort(["asof", "symbol"])
    path.parent.mkdir(parents=True, exist_ok=True)
    combined.write_parquet(path)
    return int(combined.select(pl.col("asof").n_unique()).item())


def load_snapshots(name: str, *, data_dir: Path | None = None) -> list[tuple[date, set[str]]]:
    """누적 스냅샷을 시간순 (asof, 종목집합) 리스트로 읽는다."""
    path = snapshots_path(name, data_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"스냅샷 로그가 없습니다: {path} — 먼저 record_snapshot 으로 누적하세요."
        )
    df = pl.read_parquet(path).sort("asof")
    out: list[tuple[date, set[str]]] = []
    for key, group in df.group_by("asof", maintain_order=True):
        out.append((key[0], set(group["symbol"].to_list())))
    return sorted(out, key=lambda t: t[0])


def rebuild_universe(name: str, *, data_dir: Path | None = None) -> int:
    """누적 스냅샷에서 멤버십 구간을 복원해 universe_path 에 저장한다(load_universe 가 읽음).

    Returns:
        복원된 멤버십(구간) 개수.
    """
    snapshots = load_snapshots(name, data_dir=data_dir)
    memberships = snapshots_to_memberships(snapshots)
    path = universe_path(name, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    memberships_to_frame(memberships).write_parquet(path)
    return len(memberships)
