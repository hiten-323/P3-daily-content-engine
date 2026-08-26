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

# EVERY live truthfulness incident traced back to this file.
#
# The previous templates hardcoded, verbatim:
#   "Most people don't know their daily coffee has 40% chicory filler."
#       -> the fabricated statistic that published to the grid
#   "Try your first cup free. Link in bio."
#       -> an offer that has never existed
#   "Slide 1: It tastes bitter after 2 minutes"
#       -> the scaffolding leak that rendered into carousel images
#   "India spends Rs 6,000 crore...", "grew 34% YoY", "India's first"
#       -> unsourced market statistics and an unsubstantiated superlative
#
# None of it came from the LLM. The engine falls back here whenever generation
# fails, so the scrubbers, claim verifier and gates built downstream were all
# catching a defect that shipped with the fallback itself. Fallback content is
# published unattended on the worst days — it must be the SAFEST content in the
# repo, not the least reviewed.
#
# Rules for anything added here:
#   - only facts verifiable from our own label (see claim_verifier.VERIFIED_FACTS)
#   - no claims about what any other brand contains
#   - no market statistics, no superlatives, no offers
#   - no "Slide N:" / "Frame N:" scaffolding in viewer-facing copy
#   - must satisfy the schema, or the publish gate silently drops it
# tests/test_fallback_safety.py enforces all of the above.

_EVERGREEN: list[dict] = [
    {
        "type":      "reel",
        "hook":      "Turn the jar around before you buy it.",
        "hook_text": "Turn the jar around before you buy it.",
        "hook_spoken": "The front of the pack is marketing. The back is the recipe.",
        "hook_text_overlay": "READ THE BACK",
        "frames": [
            {"on_screen": "READ THE BACK",
             "spoken": "The front of the pack is marketing. The back is the recipe."},
            {"on_screen": "INGREDIENTS",
             "spoken": "Find the ingredient list. Read every line, not just the first."},
            {"on_screen": "WHAT'S IN OURS",
             "spoken": "Purity Beans lists one thing: coffee. Zero chicory, nothing added."},
            {"on_screen": "ONE LINE",
             "spoken": "Coffee needs one ingredient. Anything else is worth knowing about."},
            {"on_screen": "YOUR TURN",
             "spoken": "Check the jar in your kitchen tonight and see what it says."},
        ],
        "body":    "Purity Beans is 100% coffee. Zero chicory, no additives, no preservatives.",
        "caption": ("The front of a coffee pack is marketing. The back is the recipe.\n\n"
                    "Purity Beans lists one ingredient: coffee. Zero chicory, nothing added.\n\n"
                    "Check the jar in your kitchen tonight.\n\np3online.in"),
        "cta":     "Read the label, then shop at p3online.in",
        "comment_trigger": "What does the label on your jar actually say?",
        "save_trigger":    "Save this for your next grocery run.",
        "share_trigger":   "Send this to whoever buys the coffee in your house.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "audio":   "Quiet kitchen ambience, no music bed — the spoken line carries it.",
        "loop_ending": "Ends on the jar being turned around, which is where it opens — the last frame reads as the first.",
        "angle":   "EXPOSE",
        "source":  "evergreen_template",
    },
    {
        "type":  "carousel",
        "hook":  "Three things to check on a coffee label",
        "title": "Three things to check on a coffee label",
        "slides": [
            {"slide": 1, "heading": "Read the ingredient list",
             "body": "It is on the back, usually in the smallest type on the pack.",
             "visual": "Close-up of an ingredient panel, jar turned to camera"},
            {"slide": 2, "heading": "Count the ingredients",
             "body": "Coffee needs one. Anything else is there for a reason worth knowing.",
             "visual": "Finger tracing down a short ingredient list"},
            {"slide": 3, "heading": "Look for chicory by name",
             "body": "It is a root, not a bean, and it is listed when present.",
             "visual": "Ingredient panel with the word chicory in frame"},
            {"slide": 4, "heading": "Check the order",
             "body": "Ingredients are listed by weight, so the first one is the bulk of it.",
             "visual": "Ingredient panel with the first line highlighted"},
            {"slide": 5, "heading": "What ours says",
             "body": "Purity Beans lists coffee. Zero chicory, no additives.",
             "visual": "Purity Beans jar, label facing camera"},
            # The schema requires the website on the final slide — the carousel
            # is the one format where the CTA lives in the image, not the caption.
            {"slide": 6, "heading": "Do it tonight",
             "body": "Turn around the jar in your kitchen and read the list. "
                     "Purity Beans — p3online.in",
             "visual": "Hand turning a jar on a kitchen counter"},
        ],
        "caption": ("Three things worth checking on any coffee label.\n\n"
                    "Purity Beans lists one ingredient: coffee.\n\n"
                    "Zero chicory, no additives.\n\np3online.in"),
        "cta":     "Shop pure coffee at p3online.in",
        "comment_trigger": "Which of the three surprised you?",
        "save_trigger":    "Save this for your next grocery run.",
        "share_trigger":   "Share with someone who drinks instant daily.",
        "hashtags": "#PurityBeans #PureCoffee #ZeroChicory #CoffeeIndia #ReadTheLabel",
        "source":  "evergreen_template",
    },
    {
        "type":    "instagram_post",
        "hook":    "One ingredient. That is the whole list.",
        "body":    "Purity Beans is 100% coffee. Zero chicory, no additives, no preservatives.",
        "caption": ("One ingredient. That is the whole list.\n\n"
                    "Purity Beans is 100% coffee — zero chicory, no additives, "
                    "no preservatives.\n\nTurn your jar around and compare.\n\np3online.in"),
        "cta":     "Shop at p3online.in",
        "comment_trigger": "How many ingredients are on your jar?",
        "save_trigger":    "Save this for your next grocery run.",
        "share_trigger":   "Send this to a fellow coffee drinker.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeLover",
        "source":  "evergreen_template",
    },
    {
        "type": "linkedin_post",
        "hook": "We built a coffee brand around a shorter ingredient list",
        "body": (
            "Instant coffee in India is a category where the ingredient list is "
            "the most informative thing on the pack, and the least read.\n\n"
            "We built Purity Beans around a simple constraint: one ingredient. "
            "Coffee. Zero chicory, no additives, no preservatives.\n\n"
            "That constraint decides sourcing, cost and shelf positioning — it is "
            "a harder product to make and an easier one to explain.\n\n"
            "For distributors and retailers interested in stocking it, my DMs are open.\n\n"
            "p3online.in"
        ),
        "cta": "Distributor and retailer enquiries welcome in DMs",
        "hashtags": "#Coffee #FMCG #IndianBrands #Distribution #PurityBeans",
        "source": "evergreen_template",
    },
]

_DISTRIBUTOR_TEMPLATES: list[dict] = [
    {
        "type": "linkedin_post",
        "hook": "What our distributors ask about first",
        "body": (
            "The first question is always the ingredient list, because it is what "
            "the customer asks them about at the counter.\n\n"
            "Purity Beans is 100% coffee — zero chicory, no additives, no "
            "preservatives — which makes it a straightforward product to stand "
            "behind on a shelf full of blends.\n\n"
            "We are expanding our distributor network. If you distribute FMCG and "
            "want the details, message me.\n\np3online.in"
        ),
        "cta": "DM for the distributor pack",
        "hashtags": "#FMCG #Distribution #Coffee #IndianBrands #PurityBeans",
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
        return _attach_stories(content, day_number)

    # Try last week's best content
    content = _from_best_historical(day_number)
    if content:
        logger.info("[fallback] Using best historical content")
        _send_fallback_alert("historical_best", day_number)
        return _attach_stories(content, day_number)

    # Final safety net: evergreen templates
    logger.warning("[fallback] Using evergreen templates (minimum viable output)")
    _send_fallback_alert("evergreen_templates", day_number)
    return _attach_stories(_from_evergreen(day_number), day_number)


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

    payload = {
        "day_number":     day_number,
        "reels":          reels,
        "carousel":       next((p for p in shuffle if p["type"] == "carousel"), _EVERGREEN[1]),
        "instagram_post": next((p for p in shuffle if p["type"] == "instagram_post"), _EVERGREEN[2]),
        "linkedin_post":  _DISTRIBUTOR_TEMPLATES[0],
        "_source":        "emergency_fallback_evergreen",
        "_recycled":      True,
    }
    return _attach_stories(payload, day_number)


def _attach_stories(payload: dict, day_number: int) -> dict:
    """Give fallback days a stories.story_1 so post_story is not slogan-only."""
    if not isinstance(payload, dict):
        return payload
    stories = payload.get("stories") if isinstance(payload.get("stories"), dict) else {}
    s1 = stories.get("story_1") if isinstance(stories.get("story_1"), dict) else {}
    if s1.get("headline") or s1.get("poll_question"):
        return payload
    try:
        from content_generator.publisher.story_copy import stories_block_from_content
        payload["stories"] = stories_block_from_content(payload, day_number)
    except Exception as e:
        logger.debug("[fallback] stories block skipped: %s", e)
    return payload


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
