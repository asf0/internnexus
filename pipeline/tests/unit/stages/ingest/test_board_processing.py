from __future__ import annotations

from pipeline.stages.ingest.board_processing import is_suspicious_board_drop as _is_suspicious_board_drop


def test_no_previous_snapshot_is_never_suspicious() -> None:
    assert _is_suspicious_board_drop(0, 0, ratio=0.5, min_count=20) is False
    assert _is_suspicious_board_drop(0, 5, ratio=0.5, min_count=20) is False


def test_fully_empty_fetch_is_suspicious_regardless_of_board_size() -> None:
    assert _is_suspicious_board_drop(3, 0, ratio=0.5, min_count=20) is True
    assert _is_suspicious_board_drop(500, 0, ratio=0.5, min_count=20) is True


def test_small_board_organic_turnover_is_not_suspicious() -> None:
    # Losing 1 of 3 jobs is a >50% drop by ratio, but the board is below
    # min_count, so ordinary single-job closures don't trip the guard.
    assert _is_suspicious_board_drop(3, 1, ratio=0.5, min_count=20) is False


def test_large_board_partial_drop_is_suspicious() -> None:
    # 100 -> 40 is a 60% drop on a board well above min_count.
    assert _is_suspicious_board_drop(100, 40, ratio=0.5, min_count=20) is True


def test_large_board_modest_drop_is_not_suspicious() -> None:
    # 100 -> 60 is only a 40% drop, under the 50% ratio threshold.
    assert _is_suspicious_board_drop(100, 60, ratio=0.5, min_count=20) is False


def test_drop_below_min_count_threshold_is_not_suspicious() -> None:
    # Board has exactly min_count - 1 previous jobs, so the ratio check
    # doesn't apply even though the drop is severe.
    assert _is_suspicious_board_drop(19, 1, ratio=0.5, min_count=20) is False


def test_boundary_at_min_count_applies_ratio_check() -> None:
    assert _is_suspicious_board_drop(20, 9, ratio=0.5, min_count=20) is True
    assert _is_suspicious_board_drop(20, 10, ratio=0.5, min_count=20) is False
