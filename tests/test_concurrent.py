"""Tests for the run_parallel helper."""

from __future__ import annotations

import time

import pytest

from alphamo._concurrent import run_parallel


def test_run_parallel_returns_results_in_input_order():
    tasks = [lambda i=i: i * 10 for i in range(5)]
    assert run_parallel(tasks) == [0, 10, 20, 30, 40]


def test_run_parallel_handles_empty_input():
    assert run_parallel([]) == []


def test_run_parallel_propagates_exceptions():
    def boom():
        raise RuntimeError("kaboom")

    tasks = [lambda: 1, boom, lambda: 3]
    with pytest.raises(RuntimeError, match="kaboom"):
        run_parallel(tasks)


def test_run_parallel_actually_parallelizes():
    """Four sleep(0.2) tasks must finish well under sequential 0.8s.

    Wall-clock measurement is noisy under load, so we allow generous slack
    but still assert we beat the serial bound by a margin that's impossible
    to hit serially.
    """

    def slow():
        time.sleep(0.2)
        return "done"

    started = time.monotonic()
    results = run_parallel([slow, slow, slow, slow], max_workers=4)
    elapsed = time.monotonic() - started

    assert results == ["done"] * 4
    # Serial would be ~0.8s; parallel with 4 workers ~0.2s. 0.5s gives slack.
    assert elapsed < 0.5, f"parallel run took {elapsed:.2f}s; expected <0.5s"


def test_run_parallel_respects_max_workers_under_high_task_count():
    """Eight 0.1s tasks at max_workers=4 → two rounds ≈ 0.2s, well under serial 0.8s."""

    def slow():
        time.sleep(0.1)
        return None

    started = time.monotonic()
    run_parallel([slow] * 8, max_workers=4)
    elapsed = time.monotonic() - started

    assert elapsed < 0.5, f"two-round parallel took {elapsed:.2f}s; expected <0.5s"
    assert elapsed >= 0.15, (
        f"only one round took {elapsed:.2f}s — max_workers may not be enforced"
    )


def test_run_parallel_preserves_order_even_when_tasks_finish_out_of_order():
    """A task that finishes last must still appear at its original index."""

    def slow_a():
        time.sleep(0.15)
        return "A"

    def fast_b():
        return "B"

    def medium_c():
        time.sleep(0.05)
        return "C"

    # A is the slowest; submitted first; must appear first in output.
    results = run_parallel([slow_a, fast_b, medium_c], max_workers=3)
    assert results == ["A", "B", "C"]
