"""
Run lock — prevents double execution on the same calendar day.

GitHub Actions can occasionally trigger twice (e.g. a manual re-run
overlapping with the scheduled cron). This lock ensures the full pipeline
runs exactly once per day, no matter how many processes try to start it.

Mechanism:
  - On acquire: write today's date + PID to output/.running
  - On release: delete the file
  - On check: if file exists AND date matches today → already ran → skip

The lock is date-based (not just PID-based) so a crashed run from
yesterday doesn't block today's execution.

Usage:
    from content_generator.scheduler.run_lock import RunLock

    with RunLock() as lock:
        if lock.already_ran:
            sys.exit(0)
        run_full_pipeline()
    # lock auto-released on exit
"""
from __future__ import annotations
import datetime
import logging
import os

logger = logging.getLogger(__name__)

_LOCK_FILE = os.path.join("output", ".running")


class RunLock:
    """
    Context manager that acquires/releases the daily run lock.

    Attributes:
        already_ran (bool): True if today's run already completed.
        was_acquired (bool): True if this instance holds the lock.
    """

    def __init__(self, lock_path: str = _LOCK_FILE):
        self._path        = lock_path
        self.already_ran  = False
        self.was_acquired = False

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "RunLock":
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        today = datetime.date.today().isoformat()

        if os.path.exists(self._path):
            try:
                content = open(self._path).read().strip()
                # Format: "YYYY-MM-DD|PID"
                parts   = content.split("|")
                lock_date = parts[0] if parts else ""

                if lock_date == today:
                    logger.info(
                        "[run_lock] Today's run already completed (lock: %s) — skipping",
                        content,
                    )
                    self.already_ran = True
                    return self
                else:
                    # Stale lock from a previous day — clear it
                    logger.info("[run_lock] Stale lock from %s — clearing", lock_date)
                    os.remove(self._path)
            except Exception:
                # Unreadable lock file — treat as stale
                try:
                    os.remove(self._path)
                except Exception:
                    pass

        # Write the lock
        try:
            with open(self._path, "w") as f:
                f.write(f"{today}|{os.getpid()}")
            self.was_acquired = True
            logger.info("[run_lock] Lock acquired for %s (pid=%d)", today, os.getpid())
        except Exception as e:
            logger.warning("[run_lock] Could not write lock file: %s — proceeding anyway", e)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        # Keep the lock file on success — it blocks duplicate runs for the rest of today.
        # The next day's run sees a stale date and clears it automatically.
        #
        # Only release if the run crashed mid-flight (exception raised):
        # that lets a retry attempt run again rather than being permanently locked.
        if exc_type is not None and self.was_acquired and not self.already_ran:
            logger.info("[run_lock] Run failed — releasing lock so a retry can proceed")
            self._release()
        # Don't suppress exceptions
        return False

    # ── Manual API ────────────────────────────────────────────────────────────

    def release(self) -> None:
        """Manually release the lock (called after successful completion)."""
        self._release()

    def _release(self) -> None:
        try:
            if os.path.exists(self._path):
                os.remove(self._path)
                logger.info("[run_lock] Lock released")
        except Exception as e:
            logger.warning("[run_lock] Could not release lock: %s", e)

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def is_running() -> bool:
        """Check if a run is currently in progress today (from any process)."""
        if not os.path.exists(_LOCK_FILE):
            return False
        try:
            content   = open(_LOCK_FILE).read().strip()
            lock_date = content.split("|")[0]
            return lock_date == datetime.date.today().isoformat()
        except Exception:
            return False

    @staticmethod
    def force_clear() -> None:
        """Emergency: forcibly remove all locks (use if a run crashed mid-flight)."""
        for filename in (".running", ".running_morning", ".running_evening"):
            path = os.path.join("output", filename)
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info("[run_lock] Lock %s force-cleared", filename)
            except Exception as e:
                logger.warning("[run_lock] Force clear failed for %s: %s", filename, e)
