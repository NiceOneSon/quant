from research.validation import walk_forward_splits


def test_no_lookahead_train_precedes_test() -> None:
    splits = walk_forward_splits("2015-01-01", "2025-01-01", train_days=365, test_days=180)
    assert splits, "분할이 하나는 나와야 한다"
    for s in splits:
        # 핵심 불변식: 학습은 검증보다 항상 앞선다
        assert s.train_end <= s.test_start
        assert s.test_start < s.test_end


def test_rolling_test_windows_do_not_overlap() -> None:
    splits = walk_forward_splits("2015-01-01", "2025-01-01", train_days=365, test_days=180)
    for prev, nxt in zip(splits, splits[1:], strict=False):
        assert prev.test_end <= nxt.test_start


def test_anchored_keeps_train_start_fixed() -> None:
    splits = walk_forward_splits(
        "2015-01-01", "2025-01-01", train_days=365, test_days=180, anchored=True
    )
    assert len({s.train_start for s in splits}) == 1  # 확장 윈도우
