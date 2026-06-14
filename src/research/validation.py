"""워크포워드 / 아웃오브샘플(OOS) 검증. 데이터 스노핑·과적합을 거른다.

영상에서 데이터 고문(data snooping)과 과적합을 경고하고, 대회 평가가 25년 상반기
아웃오브샘플 구간에서 갈렸다고 한 부분을 구조로 옮긴 자리. 인샘플에서만 좋고 OOS에서
꺾이는 전략을 걸러내는 것이 목적이다.

핵심 불변식: 각 분할에서 학습(train) 구간은 검증(test) 구간보다 항상 앞선다.
test 구간 데이터로 학습하거나 튜닝하면 룩어헤드/스노핑이 된다 — 구조적으로 금지.
구간은 반개구간 [start, end) 으로 다룬다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


def _parse(d: str | date) -> date:
    return d if isinstance(d, date) else date.fromisoformat(d)


@dataclass(frozen=True)
class Split:
    """하나의 워크포워드 분할. 모든 구간은 반개구간 [start, end)."""

    train_start: date
    train_end: date
    test_start: date
    test_end: date

    def __post_init__(self) -> None:
        # 룩어헤드 방지: 학습 구간은 검증 구간보다 앞서야 한다.
        if self.train_end > self.test_start:
            raise ValueError("train_end 가 test_start 보다 뒤입니다 — 룩어헤드입니다.")


def walk_forward_splits(
    start: str | date,
    end: str | date,
    *,
    train_days: int,
    test_days: int,
    step_days: int | None = None,
    anchored: bool = False,
) -> list[Split]:
    """[start, end) 를 워크포워드 분할로 자른다.

    Args:
        train_days: 학습 윈도우 길이(일).
        test_days: 검증(OOS) 윈도우 길이(일).
        step_days: 다음 분할까지 전진 거리. 기본은 test_days(검증 구간 비중첩).
        anchored: True 면 확장 윈도우(학습 시작이 start 에 고정), False 면 롤링 윈도우.

    Returns:
        시간순 Split 리스트. 각 Split 은 train_end <= test_start 를 보장한다.
    """
    if train_days <= 0 or test_days <= 0:
        raise ValueError("train_days, test_days 는 양수여야 합니다.")
    step = test_days if step_days is None else step_days
    if step <= 0:
        raise ValueError("step_days 는 양수여야 합니다.")

    begin = _parse(start)
    finish = _parse(end)
    splits: list[Split] = []
    cursor = begin
    while True:
        train_start = begin if anchored else cursor
        train_end = cursor + timedelta(days=train_days)
        test_start = train_end
        test_end = test_start + timedelta(days=test_days)
        if test_end > finish:
            break
        splits.append(Split(train_start, train_end, test_start, test_end))
        cursor += timedelta(days=step)
    return splits
