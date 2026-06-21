"""
LLM router — circuit breaker, rate limiter, retry, cost tracking.

Call order: Gemini → DeepSeek → Cerebras → Groq → OpenRouter
Each provider has an independent circuit breaker: after 3 consecutive failures
it is disabled for 15 minutes before being retried.
A threading.Semaphore(2) limits concurrent outbound API calls to prevent
burst rate-limiting when the pipeline runs tasks in parallel.
"""
import time
import logging
from threading import Semaphore, Lock
from dataclasses import dataclass, field

from content_generator.providers import gemini, groq, openrouter, deepseek, cerebras
from content_generator.parsers.json_parser import extract

logger = logging.getLogger(__name__)

# ── Rate limiter — max 2 concurrent API calls across all providers ────────────
_API_SEMAPHORE = Semaphore(2)

_RETRY_STATUSES      = {429, 500, 502, 503, 504}
_CIRCUIT_COOLDOWN_S  = 900   # 15 minutes
_CIRCUIT_TRIP_AT     = 3     # failures before tripping
_QUOTA_COOLDOWN_S    = 3600  # 1 hour — 429 quota errors cool for longer
_QUOTA_TRIP_AT       = 2     # trip immediately on 2nd quota error


# ── Circuit breaker ───────────────────────────────────────────────────────────

@dataclass
class _ProviderState:
    name: str
    _fail_count: int   = field(default=0, repr=False)
    _healthy: bool     = field(default=True, repr=False)
    _cooldown_until: float = field(default=0.0, repr=False)
    _lock: Lock        = field(default_factory=Lock, repr=False)

    def is_available(self) -> bool:
        with self._lock:
            if self._healthy:
                return True
            if time.time() > self._cooldown_until:
                logger.info("Circuit breaker RESET for %s", self.name)
                self._healthy    = True
                self._fail_count = 0
            return self._healthy

    def record_success(self) -> None:
        with self._lock:
            self._fail_count = 0
            self._healthy    = True

    def record_failure(self, quota_error: bool = False) -> None:
        with self._lock:
            self._fail_count += 1
            trip_at   = _QUOTA_TRIP_AT    if quota_error else _CIRCUIT_TRIP_AT
            cooldown  = _QUOTA_COOLDOWN_S if quota_error else _CIRCUIT_COOLDOWN_S
            if self._fail_count >= trip_at:
                self._healthy        = False
                self._cooldown_until = time.time() + cooldown
                reason = "quota exhausted" if quota_error else "repeated failures"
                logger.warning(
                    "Circuit breaker OPEN for %s (%s) — disabled for %d min",
                    self.name, reason, cooldown // 60,
                )


_STATES = {
    "gemini":      _ProviderState("gemini"),
    "deepseek":    _ProviderState("deepseek"),
    "cerebras":    _ProviderState("cerebras"),
    "groq":        _ProviderState("groq"),
    "openrouter":  _ProviderState("openrouter"),
}

# Accumulated usage across the run — read by pipeline/generator.py
_usage_log: list[dict] = []
_usage_lock = Lock()


def get_usage_log() -> list[dict]:
    with _usage_lock:
        return list(_usage_log)


def _record_usage(label: str, provider: str, usage: dict) -> None:
    with _usage_lock:
        _usage_log.append({
            "label":             label,
            "provider":          provider,
            "prompt_tokens":     usage.get("prompt_tokens", 0) or 0,
            "completion_tokens": usage.get("completion_tokens", 0) or 0,
        })


# ── Provider call table ───────────────────────────────────────────────────────

_PROVIDERS = [
    ("groq",       groq.call),
    ("gemini",     gemini.call),
    ("cerebras",   cerebras.call),
    ("deepseek",   deepseek.call),
    ("openrouter", openrouter.call),
]


def any_provider_available() -> bool:
    """Return True if at least one provider has an API key configured."""
    from content_generator.providers import groq, cerebras, openrouter, gemini, deepseek
    checks = [
        groq.get_key(),
        cerebras.get_key(),
        openrouter.get_key(),
        gemini.get_key(),
        deepseek.get_key(),
    ]
    return any(k for k in checks if k)


def _try_provider(
    name: str,
    call_fn,
    prompt: str,
    max_tokens: int,
    label: str,
    retries: int,
) -> str | None:
    """
    Attempt a single provider with exponential backoff on retryable status codes.
    Returns raw text on success, None on permanent failure.
    """
    state = _STATES[name]
    if not state.is_available():
        logger.debug("Skipping %s — circuit breaker open", name)
        return None

    for attempt in range(retries):
        wait = 15 * (2 ** attempt)   # 15s, 30s, 60s  (was 30/60/120)
        with _API_SEMAPHORE:
            text, usage = call_fn(prompt, max_tokens)

        if text is not None:
            state.record_success()
            _record_usage(label, name, usage)
            logger.info("[llm] ✅ %s -> %s (%d chars)", label, name, len(text))
            return text

        status      = usage.get("status_code", 0)
        is_quota    = status == 429

        if is_quota:
            # 429 quota error — record immediately, trip after 2 hits, skip retries
            state.record_failure(quota_error=True)
            logger.warning("[llm] %s QUOTA EXHAUSTED (429) — skipping to next provider", name)
            return None   # don't wait, don't retry — move to next provider immediately

        if status in _RETRY_STATUSES:
            logger.warning("[llm] %s %s status %s — retry in %ds", label, name, status, wait)
            time.sleep(wait)
        else:
            # Non-retryable error — break immediately
            state.record_failure()
            return None

    state.record_failure()
    return None


def call(prompt: str, label: str, max_tokens: int = 3000) -> dict:
    """
    Route a prompt through providers in order, parse the response, return a dict.
    Injects the centralized brand system prompt instructions before routing.
    Raises RuntimeError if all providers fail.
    """
    logger.info("[pipeline] Generating %s ...", label)

    from content_generator.core.brand_guard import build_system_prompt
    system_rules = build_system_prompt()
    full_prompt = f"SYSTEM RULES:\n{system_rules}\n\nUSER REQUEST:\n{prompt}"

    for name, fn in _PROVIDERS:
        retries = 3 if name == "gemini" else 2 if name in ("groq", "deepseek", "cerebras") else 4
        raw = _try_provider(name, fn, full_prompt, max_tokens, label, retries)
        if raw:
            data = extract(raw)
            logger.info("[pipeline] ✅ %s done", label)
            return data

    raise RuntimeError(
        f"All LLM providers failed for '{label}'. "
        "Set GEMINI_API_KEY or GROQ_API_KEY in GitHub Secrets."
    )
