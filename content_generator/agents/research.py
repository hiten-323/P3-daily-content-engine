"""
Research agent — aggregates all intelligence before content generation.

Collects:
  • Today's trends (Google Trends / Reddit / baseline)
  • Competitor intelligence (top hooks from tracked brands)
  • Strategy context (which hooks are winning based on historical data)
  • Memory stats (how many pieces stored)

Returns a single unified context dict that the generator injects into prompts.
Every source degrades gracefully — missing modules return empty strings/dicts.
"""
import logging

logger = logging.getLogger(__name__)


def run_research() -> dict:
    """
    Execute all research tasks and return a unified context dict.

    Keys returned:
      trends               — list of trend dicts
      trends_prompt_block  — formatted string for prompt injection
      competitor_prompt_block — formatted string for prompt injection
      strategy_context     — dict from optimizer (empty if no data yet)
      memory_stats         — dict with total_stored count etc.
    """
    ctx: dict = {
        "trends":                [],
        "trends_prompt_block":   "",
        "competitor_prompt_block": "",
        "strategy_context":      {},
        "memory_stats":          {},
    }

    # ── Trends ────────────────────────────────────────────────────────────────
    try:
        from content_generator.intelligence.trends import (
            get_todays_trends,
            format_trends_for_prompt,
        )
        trends = get_todays_trends()
        ctx["trends"]             = trends
        ctx["trends_prompt_block"] = format_trends_for_prompt(trends)
        logger.info("[research] %d trends fetched", len(trends))
    except Exception as e:
        logger.warning("[research] Trends failed: %s", e)

    # ── Competitor intelligence ───────────────────────────────────────────────
    try:
        from content_generator.intelligence.competitors import format_competitor_context
        ctx["competitor_prompt_block"] = format_competitor_context(limit=3)
        logger.info("[research] Competitor context loaded")
    except Exception as e:
        logger.warning("[research] Competitor intel failed: %s", e)

    # ── Performance optimizer ─────────────────────────────────────────────────
    try:
        from content_generator.analytics.optimizer import get_strategy_context
        ctx["strategy_context"] = get_strategy_context()
        if ctx["strategy_context"]:
            logger.info(
                "[research] Strategy: top hook=%s (%.1f viral score)",
                ctx["strategy_context"].get("top_performing_hook", "?"),
                ctx["strategy_context"].get("top_hook_viral_score", 0),
            )
    except Exception as e:
        logger.warning("[research] Strategy context failed: %s", e)

    # ── Semantic memory stats ─────────────────────────────────────────────────
    try:
        from content_generator.memory.semantic import memory_stats
        ctx["memory_stats"] = memory_stats()
    except Exception as e:
        logger.warning("[research] Memory stats failed: %s", e)

    return ctx
