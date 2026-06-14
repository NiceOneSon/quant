from datetime import date
from pathlib import Path

import pytest

from data_layer.ingest import ingest_universe_snapshot
from data_layer.universe import Membership, load_universe, members_asof
from data_layer.universe_snapshots import (
    load_snapshots,
    rebuild_universe,
    record_snapshot,
)


def test_record_snapshot_is_idempotent_per_asof(tmp_path: Path) -> None:
    record_snapshot("u", date(2024, 1, 1), ["A", "B"], data_dir=tmp_path)
    record_snapshot("u", date(2024, 1, 1), ["A", "B", "C"], data_dir=tmp_path)  # 같은 asof 교체
    record_snapshot("u", date(2024, 2, 1), ["A", "C"], data_dir=tmp_path)
    snaps = load_snapshots("u", data_dir=tmp_path)
    assert [d for d, _ in snaps] == [date(2024, 1, 1), date(2024, 2, 1)]
    assert snaps[0][1] == {"A", "B", "C"}  # 교체본


def test_rebuild_reconstructs_membership_intervals(tmp_path: Path) -> None:
    # 스냅샷 누적: B 는 2월에 사라짐(편출), C 는 2월에 신규
    record_snapshot("u", date(2024, 1, 1), ["A", "B"], data_dir=tmp_path)
    record_snapshot("u", date(2024, 2, 1), ["A", "C"], data_dir=tmp_path)
    rebuild_universe("u", data_dir=tmp_path)

    members = load_universe("u", data_dir=tmp_path)
    got = {(m.symbol, m.added, m.removed) for m in members}
    assert got == {
        ("A", date(2024, 1, 1), None),
        ("B", date(2024, 1, 1), date(2024, 2, 1)),  # 편출 → removed 기록 (생존편향 방지)
        ("C", date(2024, 2, 1), None),
    }
    # 편출된 B 도 그 시점엔 유니버스에 있었다
    assert members_asof(members, "2024-01-15") == {"A", "B"}
    assert members_asof(members, "2024-02-15") == {"A", "C"}


def test_ingest_universe_snapshot_accumulates(tmp_path: Path) -> None:
    class _FakeSource:
        def __init__(self, symbols: list[str]) -> None:
            self._symbols = symbols

        def fetch(self, name: str) -> list[Membership]:
            return [Membership(s, added=date(2024, 1, 1)) for s in self._symbols]

    ingest_universe_snapshot(_FakeSource(["A", "B"]), "kospi", date(2024, 1, 1), data_dir=tmp_path)
    ingest_universe_snapshot(_FakeSource(["A", "C"]), "kospi", date(2024, 2, 1), data_dir=tmp_path)

    members = load_universe("kospi", data_dir=tmp_path)
    assert members_asof(members, "2024-01-15") == {"A", "B"}
    assert members_asof(members, "2024-02-15") == {"A", "C"}


def test_load_snapshots_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_snapshots("nope", data_dir=tmp_path)
