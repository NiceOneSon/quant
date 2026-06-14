from datetime import date
from pathlib import Path

import polars as pl
import pytest

from data_layer.ingest import ingest_universe, normalize_memberships
from data_layer.sources import CsvUniverseSource
from data_layer.universe import (
    Membership,
    frame_to_memberships,
    load_universe,
    members_asof,
    universe_path,
)


def _raw_members(name: str, tmp: Path) -> list[Membership]:
    """ingest 가 적재한 raw 유니버스(dbt 이전)를 직접 읽어 멤버십으로 복원."""
    return frame_to_memberships(pl.read_parquet(universe_path(name, tmp)))


_CSV = (
    "symbol,added,removed\n"
    "AAA,2010-01-01,\n"
    "BBB,2010-01-01,2018-06-01\n"  # 2018 년 편출/상폐
    "CCC,2020-01-01,\n"
)


def _make_source(tmp_path: Path) -> CsvUniverseSource:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "kospi200.csv").write_text(_CSV, encoding="utf-8")
    return CsvUniverseSource(raw_dir)


def test_ingest_writes_raw_pit_universe(tmp_path: Path) -> None:
    ingest_universe(_make_source(tmp_path), "kospi200", data_dir=tmp_path)
    members = _raw_members("kospi200", tmp_path)

    assert {m.symbol for m in members} == {"AAA", "BBB", "CCC"}
    # 저장→로드 후에도 시점 조회가 생존편향 없이 동작해야 한다
    assert members_asof(members, "2017-01-01") == {"AAA", "BBB"}
    assert members_asof(members, "2019-01-01") == {"AAA"}
    assert members_asof(members, "2021-01-01") == {"AAA", "CCC"}


def test_normalize_rejects_removed_before_added() -> None:
    bad = [Membership("X", added=date(2020, 1, 1), removed=date(2019, 1, 1))]
    with pytest.raises(ValueError):
        normalize_memberships(bad)


def test_normalize_rejects_overlapping_intervals() -> None:
    # 같은 종목 구간이 겹침 (2018 편출인데 2017 재편입)
    bad = [
        Membership("X", added=date(2010, 1, 1), removed=date(2018, 1, 1)),
        Membership("X", added=date(2017, 1, 1), removed=None),
    ]
    with pytest.raises(ValueError):
        normalize_memberships(bad)


def test_normalize_allows_reentry_with_gap() -> None:
    # 편출 후 갭을 두고 재편입 → 허용
    ok = [
        Membership("X", added=date(2010, 1, 1), removed=date(2015, 6, 1)),
        Membership("X", added=date(2018, 1, 1), removed=None),
    ]
    assert len(normalize_memberships(ok)) == 2


def test_historical_csv_injection_reentry(tmp_path: Path) -> None:
    # 상폐 종목 + 재편입을 포함한 과거 멤버십 CSV 주입 → PIT 조회
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "hist.csv").write_text(
        "symbol,added,removed\n"
        "005930,2010-01-01,\n"
        "068270,2010-01-01,2015-06-01\n"  # 편출
        "068270,2018-01-01,\n",  # 재편입
        encoding="utf-8",
    )
    ingest_universe(CsvUniverseSource(raw_dir), "hist", data_dir=tmp_path)
    members = _raw_members("hist", tmp_path)

    assert members_asof(members, "2012-01-01") == {"005930", "068270"}
    assert members_asof(members, "2016-01-01") == {"005930"}  # 편출 구간
    assert members_asof(members, "2019-01-01") == {"005930", "068270"}  # 재편입 후


def test_load_universe_requires_mart(tmp_path: Path) -> None:
    # 소비 레이어(load_universe)는 dbt 마트를 읽음 → 마트 없으면 에러
    with pytest.raises(FileNotFoundError):
        load_universe("does_not_exist", marts_dir=tmp_path)
