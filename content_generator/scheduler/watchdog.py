"""
Watchdog — monitors pipeline execution and alerts on failures.

Features:
  • Per-step timeout enforcement via threading.Timer
  • Structured run log (output/run_log.json)
  • Alert dispatch: console (always), email (if configured), webhook (if configured)

Environment variables:
  ALERT_WEBHOOK_URL    — Slack/Discord/custom webhook for failure alerts
  ALERT_EMAIL_TO       — email address for failure notifications (uses SMTP_* config)
  WATCHDOG_TIMEOUT_S   — per-step timeout in seconds (default 600)
"""
import json
import logging
import os
import threading
import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_TIMEOUT_S      = int(os.getenv("WATCHDOG_TIMEOUT_S", "600"))
_WEBHOOK_URL    = os.getenv("ALERT_WEBHOOK_URL", "")
_ALERT_EMAIL    = os.getenv("ALERT_EMAIL_TO", "")
_RUN_LOG_PATH   = os.path.join("output", "run_log.json")


# ── Context manager ───────────────────────────────────────────────────────────

@contextmanager
def timed_step(label: str, timeout_s: int = None):
    """
    Context manager that enforces a timeout on a code block.
    Logs start/end and records to run_log.json.

    Usage:
        with timed_step("content_generation", timeout_s=300):
            content = generate_daily_content()
    """
    deadline = timeout_s or _TIMEOUT_S
    start    = datetime.datetime.now()
    timer    = None
    timed_out = threading.Event()

    def _on_timeout():
        timed_out.set()
        logger.error("[watchdog] TIMEOUT: %s exceeded %ds", label, deadline)
        _alert(f"TIMEOUT: {label} exceeded {deadline}s")

    timer = threading.Timer(deadline, _on_timeout)
    timer.daemon = True
    logger.info("[watchdog] START: %s (timeout=%ds)", label, deadline)
    timer.start()

    error = None
    try:
        yield
    except Exception as e:
        error = e
        logger.error("[watchdog] FAIL: %s — %s", label, e)
        _alert(f"PIPELINE FAILURE: {label}\nError: {e}")
        raise
    finally:
        timer.cancel()
        elapsed = (datetime.datetime.now() - start).total_seconds()
        status  = "timeout" if timed_out.is_set() else ("fail" if error else "ok")
        _log_run(label, status, elapsed, str(error) if error else "")
        logger.info("[watchdog] END: %s — %s in %.1fs", label, status, elapsed)


# ── Alert dispatch ────────────────────────────────────────────────────────────

def _alert(message: str) -> None:
    """Dispatch alert to all configured channels."""
    _alert_console(message)
    _alert_webhook(message)
    _alert_email(message)


def _alert_console(message: str) -> None:
    print(f"\n!!! PURITY BEANS ENGINE ALERT !!!\n{message}\n")


def _alert_webhook(message: str) -> None:
    if not _WEBHOOK_URL:
        return
    try:
        import urllib.request
        import urllib.error
        payload = json.dumps({"text": f":warning: *Purity Beans Engine Alert*\n{message}"})
        req = urllib.request.Request(
            _WEBHOOK_URL,
            data=payload.encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10):
            pass
        logger.info("[watchdog] Alert sent to webhook")
    except Exception as e:
        logger.warning("[watchdog] Webhook alert failed: %s", e)


def _alert_email(message: str) -> None:
    if not _ALERT_EMAIL:
        return
    try:
        import smtplib
        from email.mime.text import MIMEText
        from content_generator.dashboard.weekly_summary import (
            _EMAIL_FROM, _SMTP_HOST, _SMTP_PORT, _SMTP_PASS,
        )
        if not all([_EMAIL_FROM, _SMTP_PASS]):
            return
        msg            = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = "ALERT: Purity Beans Content Engine"
        msg["From"]    = _EMAIL_FROM
        msg["To"]      = _ALERT_EMAIL
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
            server.starttls()
            server.login(_EMAIL_FROM, _SMTP_PASS)
            server.send_message(msg)
        logger.info("[watchdog] Alert emailed to %s", _ALERT_EMAIL)
    except Exception as e:
        logger.warning("[watchdog] Email alert failed: %s", e)


# ── Run log ───────────────────────────────────────────────────────────────────

def _log_run(label: str, status: str, elapsed: float, error: str = "") -> None:
    """Append a run record to output/run_log.json."""
    try:
        os.makedirs("output", exist_ok=True)
        log = []
        if os.path.exists(_RUN_LOG_PATH):
            with open(_RUN_LOG_PATH) as f:
                log = json.load(f)
        log.append({
            "label":      label,
            "status":     status,
            "elapsed_s":  round(elapsed, 1),
            "error":      error,
            "timestamp":  datetime.datetime.now().isoformat(timespec="seconds"),
        })
        # Keep last 200 run records
        with open(_RUN_LOG_PATH, "w") as f:
            json.dump(log[-200:], f, indent=2)
    except Exception as e:
        logger.debug("[watchdog] Log write failed: %s", e)


def get_recent_runs(limit: int = 20) -> list[dict]:
    """Return the last N run records from the log."""
    try:
        if os.path.exists(_RUN_LOG_PATH):
            with open(_RUN_LOG_PATH) as f:
                log = json.load(f)
            return log[-limit:]
    except Exception:
        pass
    return []


def get_failure_rate(label: str = None, hours: int = 24) -> float:
    """Return the failure rate (0.0–1.0) for a label in the last N hours."""
    runs = get_recent_runs(limit=100)
    cutoff = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
    relevant = [r for r in runs if r["timestamp"] >= cutoff]
    if label:
        relevant = [r for r in relevant if r["label"] == label]
    if not relevant:
        return 0.0
    failures = sum(1 for r in relevant if r["status"] != "ok")
    return round(failures / len(relevant), 2)
