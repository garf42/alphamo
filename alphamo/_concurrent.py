"""Small ThreadPoolExecutor wrapper for parallelizing I/O-bound LLM calls.

Used by the curator (parallel classify-per-finding), Stage 3 adversarial
scrutiny (parallel framings), and the cascade.

Anthropic's SDK is thread-safe; the Pydantic models being passed are
immutable. We're parallelizing I/O wait time, not contending shared state.

Two helpers:
  - `run_parallel`: raises on first task failure. The caller's
    operation is aborted on any sub-task exception. Used where any
    failure means the whole operation can't proceed.
  - `run_parallel_collect_results`: returns successes AND failures as
    `list[T | Exception]` so the caller can decide per-task what to do.
    Used by Sprint 4's Stage 3 adversarial path so a single framing's
    transient failure doesn't kill the whole candidate evaluation.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

T = TypeVar("T")

DEFAULT_MAX_WORKERS = 4


def run_parallel(
    tasks: list[Callable[[], T]],
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> list[T]:
    """Run zero-arg callables concurrently and return their results IN ORDER.

    Exceptions from any task propagate on `.result()` — the helper does not
    swallow them. If multiple tasks raise, only the first encountered (in
    submission order) is re-raised; the others are silently dropped, which
    is fine for callers where one failure aborts the whole operation.

    With `max_workers=4` and 8 tasks, two rounds of 4 execute back-to-back;
    wall-clock approaches `2 * single_task_duration` instead of `8 *`.
    """
    if not tasks:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(task) for task in tasks]
        return [f.result() for f in futures]


def run_parallel_collect_results(
    tasks: list[Callable[[], T]],
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> list[T | Exception]:
    """Run zero-arg callables concurrently; return per-task result OR exception.

    Like `run_parallel` but exceptions are CAUGHT and returned in place of
    the task's result, preserving submission-order alignment. The caller
    decides what to do with each (e.g., Stage 3 adversarial uses the
    success / failure split to apply a 5-of-9-success threshold).

    Sprint 4 motivation: a single API failure within a parallel batch
    must not abort the whole batch. The caller's failure semantics live
    in the caller, not in this helper.
    """
    if not tasks:
        return []
    results: list[T | Exception] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(task) for task in tasks]
        for future in futures:
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001 — preserved for caller
                results.append(exc)
    return results
