"""Small ThreadPoolExecutor wrapper for parallelizing I/O-bound LLM calls.

Used by the curator (parallel classify-per-finding), Stage 4 (parallel
adversarial framings), and the cascade (parallel Stage 3 / Stage 4 once
Stage 4 ships in part 2).

Anthropic's SDK is thread-safe; the Pydantic models being passed are
immutable. We're parallelizing I/O wait time, not contending shared state.
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
    is fine for our use case (one LLM failure aborts the operation).

    With `max_workers=4` and 8 tasks, two rounds of 4 execute back-to-back;
    wall-clock approaches `2 * single_task_duration` instead of `8 *`.
    """
    if not tasks:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(task) for task in tasks]
        return [f.result() for f in futures]
