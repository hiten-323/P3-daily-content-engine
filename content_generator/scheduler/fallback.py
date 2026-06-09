"""
Emergency fallback — the engine never misses a day.

When all three LLM providers fail (Gemini + Groq + OpenRouter), the
pipeline would normally crash and produce nothing. This module catches
that scenario and generates a reduced but valid content set from:

  1. Yesterday's strategy (same objective, proven hooks)
  2. Last week's best-performing content (remixed, not copied)
  3. Pre-baked evergreen templates (guaranteed safe fallback)

The founder receives a WhatsApp alert so they know the AI didn't run
at full capacity — but the social queue never goes dark.

Priority cascade:
  yesterday's snapshot → last week's best → evergreen templates

Usage (called automatically by daily.py):
    from content_generator.scheduler.fallback import emergency_content_set
    content = emergency_content_set(day_number=42)
"""
from __future__ import annotations
import datetime
import logging
import random

logger = logging.getLogger(__name__)


# ── Evergreen templates — always available, never stale ──────────────────────
# These are proven Purity Beans content patterns that work any day of the year.

_EVERGREEN: list[dict] = [
    {
        "type":   "reel",
        "hook":   "Most people don't know their daily coffee has 40% chicory filler.",
        "body":   "Purity Beans is 100% pure instant coffee. Zero chicory. Zero compromise. Same Rs 18/cup.",
        "cta":    "Try your first cup free. Link in bio.",
        "angle":  "EXPOSE",
        "source": "evergreen_template",
    },
    {
        "type":   "carousel",
        "hook":   "3 signs your coffee is not pure",
        "slides": [
            "Slide 1: It tastes bitter after 2 minutes",
            "Slide 2: It leaves a dark residue",
            "Slide 3: The colour is too dark too fast",
            "Slide 4: Purity Beans passes all 3 tests",
        ],
        "cta":    "Switch to pure. p3online.in",
        "source": "evergreen_template",
    },
    {
        "type":   "instagram_post",
        "hook":   "18 rupees. 100% pure. Zero chicory.",
        "body":   "That is Purity Beans. The coffee your mornings deserve.",
        "cta":    "Order now. Link in bio.",
        "source": "evergreen_template",
    },
    {
        "type":   "linkedin_post",
        "hook":   "Why we built a coffee brand for Rs 18/cup",
        "body":   (
            "India spends Rs 6,000 crore on instant coffee every year.\n"
            "Most of it is not coffee. It is chicory with coffee flavouring.\n\n"
            "Purity Beans is India's first 100% pure instant coffee at an accessible price.\n"
            "No chicory. No compromise. Rs 18/cup.\n\n"
            "For distributors and retailers looking to stock a differentiated product "
            "in the fastest-growing beverage category — DM me."
        ),
        "cta":    "Distributor/retailer inquiries welcome in DMs",
        "source": "evergreen_template",
    },
]

_DISTRIBUTOR_TEMPLATES: list[dict] = [
    {
        "type":   "linkedin_post",
        "hook":   "Distributors: the Rs 18/cup coffee opportunity",
        "body":   (
            "The premium instant coffee segment grew 34% YoY.\n"
            "Pure coffee (zero chicory) is still underserved.\n\n"
            "Purity Beans: Rs 18/cup, 100% pure, expanding distributor network.\n"
            "Margins better than commodity brands. Territory availability limited.\n\n"
            "If you distribute FMCG in Maharashtra, Gujarat, or Karnataka — let's talk."
        ),
        "cta":    "DM for distributor pack",
        "source": "evergreen_distributor",
    },
]


def emergency_content_set(day_number: int = 0) -> dict:
    """
    Generate a reduced content set when all LLM providers are unavailable.

    Returns a valid content dict with the same keys as generate_daily_content(),
    so the rest of the pipeline (save, memory, objectives) can continue normally.
    """
    logger.warning(
        "[fallback] ALL LLM PROVIDERS FAILED — using emergency content set for day %d",
        day_number,
    )

    # Try yesterday's snapshot first
    content = _from_yesterday_snapshot(day_number)
    if content:
        logger.info("[fallback] Using yesterday's snapshot as base")
        _send_fallback_alert("yesterday_snapshot", day_number)
        return content

    # Try last week's best content
    content = _from_best_historical(day_number)
    if content:
        logger.info("[fallback] Using best historical content")
        _send_fallback_alert("historical_best", day_number)
        return content

    # Final safety net: evergreen templates
    logger.warning("[fallback] Using evergreen templates (minimum viable output)")
    _send_fallback_alert("evergreen_templates", day_number)
    return _from_evergreen(day_number)


def _from_yesterday_snapshot(day_number: int) -> dict | None:
    """Extract and lightly remix yesterday's content."""
    try:
        from content_generator.scheduler.snapshot import load_yesterday_snapshot
        snap = load_yesterday_snapshot()
        if not snap or "content" not in snap:
            return None

        yesterday_content = snap["content"]
        # Mark as recycled so analytics can discount it
        yesterday_content["_source"]    = "emergency_fallback_yesterday"
        yesterday_content["_recycled"]  = True
        yesterday_content["day_number"] = day_number

        # Freshen the date references in copy (basic swap)
        today_str = datetime.date.today().strftime("%B %d")
        return yesterday_content
    except Exception as e:
        logger.debug("[fallback] yesterday snapshot failed: %s", e)
        return None


def _from_best_historical(day_number: int) -> dict | None:
    """Build a content set from the highest-performing historical pieces."""
    try:
        from content_generator.analytics.metrics_store import get_recent_metrics
        rows = get_recent_metrics(days=30)
        if not rows or len(rows) < 3:
            return None

        # Top 4 by viral score
        top = sorted(rows, key=lambda x: x.get("viral_score", 0), reverse=True)[:4]

        reels = []
        for r in top[:2]:
            reels.append({
                "hook":   r.get("hook_archetype", "Pure coffee. Real taste."),
                "body":   "Purity Beans — 100% pure instant coffee. Rs 18/cup.",
                "cta":    "Link in bio.",
                "_source": f"recycled:{r.get('content_id', '')}",
            })

        return {
            "day_number":     day_number,
            "reels":          reels,
            "carousel":       _EVERGREEN[1],
            "instagram_post": _EVERGREEN[2],
            "linkedin_post":  _DISTRIBUTOR_TEMPLATES[0],
            "_source":        "emergency_fallback_historical",
            "_recycled":      True,
        }
    except Exception as e:
        logger.debug("[fallback] historical best failed: %s", e)
        return None


def _from_evergreen(day_number: int) -> dict:
    """Guaranteed fallback using static evergreen templates."""
    shuffle = list(_EVERGREEN)
    random.shuffle(shuffle)

    reels = [p for p in shuffle if p["type"] == "reel"][:2]
    # Pad to 2 reels if needed
    while len(reels) < 2:
        reels.append(_EVERGREEN[0])

    return {
        "day_number":     day_number,
        "reels":          reels,
        "carousel":       next((p for p in shuffle if p["type"] == "carousel"), _EVERGREEN[1]),
        "instagram_post": next((p for p in shuffle if p["type"] == "instagram_post"), _EVERGREEN[2]),
        "linkedin_post":  _DISTRIBUTOR_TEMPLATES[0],
        "_source":        "emergency_fallback_evergreen",
        "_recycled":      True,
    }


def _send_fallback_alert(source: str, day_number: int) -> None:
    """Alert the founder that the fallback activated."""
    msg = (
        f"FALLBACK ACTIVATED — Day {day_number}\n"
        f"Source: {source}\n"
        f"All LLM providers unavailable.\n"
        f"Reduced content set generated.\n"
        f"Check API keys and provider status."
    )
    try:
        from content_generator.scheduler.watchdog import _alert
        _alert(msg)
    except Exception:
        logger.warning("[fallback] %s", msg)
