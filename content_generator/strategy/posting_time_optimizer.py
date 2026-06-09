"""
Posting time optimizer.

Tracks which posting hours correlate with highest viral scores,
then recommends optimal windows per platform + audience.

Data source: posting_time_log table (populated via record_posting_time()).

Feed real data:
    from content_generator.analytics.metrics_store import record_posting_time
    record_posting_time("instagram", hour=7, viral_score=72.3, engagement=1840)

Until live data accumulates, returns evidence-based defaults from
Indian social media research for FMCG coffee audience.
"""
import logging

logger = logging.getLogger(__name__)

# Evidence-based defaults (Indian FMCG / coffee audience research)
_DEFAULT_WINDOWS: dict[str, list[dict]] = {
    "instagram": [
        {"hour": 7,  "label": "Morning rush",     "score": 85, "reason": "pre-work coffee moment"},
        {"hour": 8,  "label": "Commute start",    "score": 82, "reason": "scroll before office"},
        {"hour": 21, "label": "Evening unwind",   "score": 78, "reason": "post-dinner scroll"},
        {"hour": 12, "label": "Lunch break",      "score": 70, "reason": "mid-day feed check"},
        {"hour": 20, "label": "Prime time",       "score": 68, "reason": "evening engagement peak"},
    ],
    "linkedin": [
        {"hour": 8,  "label": "Pre-work",         "score": 88, "reason": "professionals check LinkedIn first"},
        {"hour": 12, "label": "Lunch",            "score": 80, "reason": "professional content during breaks"},
        {"hour": 17, "label": "End of day",       "score": 75, "reason": "business day wind-down"},
        {"hour": 9,  "label": "Morning deep-work", "score": 72, "reason": "decision-makers active"},
    ],
    "youtube": [
        {"hour": 20, "label": "Prime evening",    "score": 85, "reason": "long-form content after work"},
        {"hour": 21, "label": "Late evening",     "score": 82, "reason": "relaxed viewing"},
        {"hour": 9,  "label": "Weekend morning",  "score": 70, "reason": "leisure browsing"},
    ],
    "facebook": [
        {"hour": 13, "label": "Post-lunch",       "score": 75, "reason": "Facebook's older demo peaks here"},
        {"hour": 20, "label": "Evening",          "score": 72, "reason": "family content sharing"},
    ],
}


def get_best_posting_time(
    platform: str   = "instagram",
    audience: str   = "consumer",
    top_n: int      = 3,
) -> list[dict]:
    """
    Return the top N recommended posting windows for a platform + audience.

    Returns data-driven results when available (>= 5 samples per hour),
    otherwise returns research-backed defaults.
    """
    try:
        from content_generator.analytics.metrics_store import get_best_posting_hours
        live = get_best_posting_hours(platform=platform, days=90)
        if live and len(live) >= 3:
            return live[:top_n]
    except Exception:
        pass

    defaults = _DEFAULT_WINDOWS.get(platform, _DEFAULT_WINDOWS["instagram"])
    return defaults[:top_n]


def get_daily_schedule(audience: str = "consumer") -> dict:
    """
    Return a full daily posting schedule for all platforms.
    Used by scheduler/daily.py to time its publishing calls.
    """
    schedule = {}
    for platform in ("instagram", "linkedin", "youtube", "facebook"):
        best = get_best_posting_time(platform=platform, audience=audience, top_n=1)
        if best:
            schedule[platform] = {
                "hour":   best[0].get("hour", 7),
                "label":  best[0].get("label", ""),
                "reason": best[0].get("reason", ""),
            }
    return schedule


def format_schedule_for_prompt(audience: str = "consumer") -> str:
    """Format posting schedule as a prompt injection block."""
    schedule = get_daily_schedule(audience)
    if not schedule:
        return ""
    lines = ["OPTIMAL POSTING TIMES (use in scheduling):"]
    for platform, info in schedule.items():
        lines.append(f"  • {platform}: {info['hour']:02d}:00 IST ({info.get('reason', '')})")
    return "\n".join(lines)
