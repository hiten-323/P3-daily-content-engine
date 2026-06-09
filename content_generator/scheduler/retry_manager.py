"""
Retry manager — wraps pipeline steps with smart retry logic.

Each step can be independently retried without rerunning the whole pipeline.
Exponential backoff with jitter prevents thundering-herd on API recovery.

Usage:
    from content_generator.scheduler.retry_manager import RetryManager

    rm = RetryManager()
    result = rm.run(
        fn=lambda: generate_daily_content(),
        label="content_generation",
        max_retries=2,
        base_wait=30,
    )
"""
import logging
import random
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class StepResult:
    """Holds the result of a pipeline step, including retry metadata."""
    def __init__(self, value=None, error=None, attempts=0):
        self.value    = value
        self.error    = error
        self.attempts = attempts
        self.success  = error is None

    def __repr__(self):
        if self.success:
            return f"StepResult(success, attempts={self.attempts})"
        return f"StepResult(FAIL, error={self.error!r}, attempts={self.attempts})"


class RetryManager:
    """
    Manages retries for individual pipeline steps.

    Backoff formula:  wait = base_wait * (2 ** attempt) + jitter
    Jitter range:     0 to base_wait seconds (prevents thundering herd)
    """

    def __init__(
        self,
        default_max_retries: int   = 3,
        default_base_wait:   float = 30.0,
        raise_on_final_fail: bool  = False,
    ):
        self.default_max_retries  = default_max_retries
        self.default_base_wait    = default_base_wait
        self.raise_on_final_fail  = raise_on_final_fail
        self._history: list[dict] = []

    def run(
        self,
        fn:          Callable[[], Any],
        label:       str   = "step",
        max_retries: int   = None,
        base_wait:   float = None,
        retryable_exceptions: tuple = (Exception,),
    ) -> StepResult:
        """
        Run fn with retry on failure.

        Args:
            fn:                   Callable that returns a value on success
            label:                Human label for logging
            max_retries:          Override default max retries
            base_wait:            Override default base wait (seconds)
            retryable_exceptions: Tuple of exception types that trigger retry

        Returns:
            StepResult with .value on success or .error on final failure
        """
        retries  = max_retries if max_retries is not None else self.default_max_retries
        wait     = base_wait   if base_wait   is not None else self.default_base_wait
        last_err = None

        for attempt in range(retries + 1):
            try:
                if attempt > 0:
                    sleep_s = wait * (2 ** (attempt - 1)) + random.uniform(0, wait)
                    logger.warning(
                        "[retry] %s — attempt %d/%d, waiting %.0fs",
                        label, attempt + 1, retries + 1, sleep_s,
                    )
                    time.sleep(sleep_s)

                value = fn()
                result = StepResult(value=value, attempts=attempt + 1)
                self._record(label, success=True, attempts=attempt + 1)
                if attempt > 0:
                    logger.info("[retry] %s — recovered on attempt %d", label, attempt + 1)
                return result

            except retryable_exceptions as e:
                last_err = e
                logger.warning("[retry] %s — attempt %d failed: %s", label, attempt + 1, e)

        self._record(label, success=False, attempts=retries + 1, error=str(last_err))
        logger.error("[retry] %s — all %d attempts failed. Last error: %s", label, retries + 1, last_err)

        if self.raise_on_final_fail:
            raise RuntimeError(f"[retry] {label} failed after {retries + 1} attempts: {last_err}") from last_err

        return StepResult(error=last_err, attempts=retries + 1)

    def run_all(
        self,
        steps: list[tuple[str, Callable]],
        stop_on_critical: bool = False,
    ) -> dict[str, StepResult]:
        """
        Run multiple steps sequentially, optionally stopping on first failure.

        Args:
            steps:             List of (label, callable) tuples
            stop_on_critical:  If True, stop pipeline on any failure

        Returns:
            Dict mapping label → StepResult
        """
        results = {}
        for label, fn in steps:
            result = self.run(fn, label=label)
            results[label] = result
            if not result.success and stop_on_critical:
                logger.error("[retry] Stopping pipeline — %s failed", label)
                break
        return results

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    def _record(self, label: str, success: bool, attempts: int, error: str = "") -> None:
        self._history.append({
            "label":    label,
            "success":  success,
            "attempts": attempts,
            "error":    error,
        })
