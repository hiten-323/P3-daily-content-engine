"""
A watchdog timeout must not throw away the emergency fallback.

2026-09-07, day 249. Every provider failed or answered with junk, so the
pipeline did exactly what it was designed to do:

    05:22:30 [scheduler] All LLM providers failed — activating emergency fallback
    05:22:30 [fallback] Using evergreen templates (minimum viable output)

and then timed_step's __exit__ raised TimeoutError and killed the run. The day
produced no content file at all. The fallback exists precisely so a bad provider
day still ships; a watchdog that discards it defeats the whole mechanism.

The budget was also unsatisfiable by construction. RetryManager backs off
60*2^(n-1) + jitter(0,60), so three attempts spend 180-300s waiting BEFORE the
attempts themselves. Against timeout_s=600 the timer fired at 05:18:37 while
attempt 3 had not yet started; generation ran on to 05:22:30, 833s in total.
"""
from __future__ import annotations

import inspect
import re

from content_generator.scheduler import daily


def _generation_step_line() -> str:
    src = inspect.getsource(daily._run_generate_slot)
    return next(l for l in src.splitlines() if 'timed_step("content_generation"' in l)


def test_generation_step_is_non_fatal() -> None:
    line = _generation_step_line()
    assert "fatal=False" in line, (
        "content_generation is fatal, so a watchdog timeout discards the emergency "
        f"fallback the step just built and the day ships nothing. Got: {line.strip()}"
    )


def test_generation_budget_covers_the_retry_policy() -> None:
    """
    Budget and retry policy must not drift apart. If the schedule cannot fit,
    the watchdog is guaranteed to fire on exactly the days the retries matter.
    """
    src = inspect.getsource(daily._run_generate_slot)
    block = src[src.index('timed_step("content_generation"'):]
    block = block[:block.index("# ── 3.")] if "# ── 3." in block else block[:2000]

    timeout = int(re.search(r'timed_step\("content_generation", timeout_s=(\d+)', block).group(1))
    retries = int(re.search(r"max_retries=(\d+)", block).group(1))
    base = int(re.search(r"base_wait=(\d+)", block).group(1))

    # Worst-case backoff before counting any generation time at all.
    worst_wait = sum(base * (2 ** (n - 1)) + base for n in range(1, retries + 1))
    assert timeout > worst_wait, (
        f"timeout_s={timeout} but the retry policy waits up to {worst_wait}s before "
        f"a single generation attempt is counted — the watchdog fires mid-schedule"
    )
    # And leave room for the attempts themselves, not just the sleeping.
    assert timeout >= worst_wait * 2, (
        f"timeout_s={timeout} leaves no room for {retries + 1} generation attempts "
        f"on top of {worst_wait}s of backoff"
    )
