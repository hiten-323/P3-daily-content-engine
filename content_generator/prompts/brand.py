"""
Shared prompt blocks injected into every module prompt:
- brand_block()       — brand context + psychology frames + banned phrases
- build_avoid_block() — last-14-day repetition guard
"""
import logging
from content_generator.rotation import WEBSITE_URL

logger = logging.getLogger(__name__)

# Imported at call time to avoid circular imports at module load
def _get_brand_config():
    from config.brand_config import BRAND, POSITIONING, HASHTAG_SETS
    return BRAND, POSITIONING, HASHTAG_SETS


def brand_block() -> str:
    BRAND, POSITIONING, _ = _get_brand_config()
    try:
        from content_generator.core.coffee_psychology import frame_prompt_block
        psych = frame_prompt_block()
    except Exception:
        psych = ""

    return (
        f"BRAND: {BRAND['name']} (by {BRAND.get('company', 'Pure Pantry Provisions')}) — premium pure instant coffee, India.\n"
        f"USP: {POSITIONING['usp']}\n"
        f"Price: Rs{POSITIONING['price_per_cup']}/cup vs Rs{POSITIONING['cafe_price']} at cafes "
        f"(10x cheaper, 100x purer)\n"
        f"Website: {WEBSITE_URL} | Tagline: \"{BRAND['tagline']}\"\n"
        f"Tone: Premium but human. Honest, not corporate. Indian in DNA.\n"
        f"\n"
        f"MANDATORY BRAND RULES — these are non-negotiable:\n"
        f"1. The brand name 'Purity Beans' MUST appear at least once in every caption, hook, body, and CTA.\n"
        f"2. The website '{WEBSITE_URL}' MUST appear in every caption and CTA.\n"
        f"3. At least one of these must appear: 'zero chicory' / '100% coffee' / 'pure coffee' / 'no chicory'.\n"
        f"4. Never use generic phrases. Every line must be specific to Purity Beans.\n"
        f"\n"
        f"{psych}\n"
        f"\n"
        f"BANNED PHRASES: \"transform your mornings\" / \"elevate your experience\" / "
        f"\"perfect cup\" / \"fuel your day\" / \"game changer\" / \"level up\" / "
        f"\"discover the difference\" / \"premium quality\"\n"
        f"Return ONLY valid JSON — no markdown fences, no text outside the JSON object."
    )


def build_avoid_block() -> str:
    """
    Reads last 14 days of published content from the DB and returns a
    DO-NOT-REPEAT block listing used archetypes, hooks, titles, and angles.
    Returns empty string on first run or DB error.
    """
    try:
        from engine.database import get_recent_content_history
        history = get_recent_content_history(days=14)
    except Exception as e:
        logger.debug("Could not load content history: %s", e)
        return ""

    if not history:
        return ""

    reel_hooks: list[str]      = []
    reel_archetypes: list[str] = []
    carousel_titles: list[str] = []
    save_mechs: list[str]      = []
    li_angles: list[str]       = []

    for entry in history:
        c    = entry.get("content", {})
        date = entry.get("date", "")
        for reel in c.get("reels", []):
            h = (reel.get("hook_text") or "").strip()
            a = (reel.get("hook_archetype") or "").strip()
            if h: reel_hooks.append(f"[{date}] {h}")
            if a: reel_archetypes.append(f"[{date}] {a[:80]}")
        for car in c.get("carousels", []) + ([c.get("carousel")] if c.get("carousel") else []):
            t = (car.get("title") or "").strip()
            m = (car.get("save_mechanic") or "").strip()
            if t: carousel_titles.append(f"[{date}] {t}")
            if m: save_mechs.append(f"[{date}] {m[:80]}")
        li = (c.get("linkedin_post") or {})
        ag = (li.get("angle") or li.get("linkedin_angle") or "").strip()
        if ag: li_angles.append(f"[{date}] {ag[:80]}")

    if not any([reel_hooks, reel_archetypes, carousel_titles]):
        return ""

    lines = [
        "DO NOT REPEAT — 14-DAY CONTENT MEMORY",
        "Use a completely different archetype, angle, and trigger for every piece today.",
        "",
    ]
    if reel_archetypes:
        lines.append("REEL ARCHETYPES USED (pick a different category):")
        lines += [f"  - {a}" for a in reel_archetypes[-8:]]
        lines.append("")
    if reel_hooks:
        lines.append("REEL HOOKS USED (completely new wording AND new trigger required):")
        lines += [f"  - {h}" for h in reel_hooks[-6:]]
        lines.append("")
    if carousel_titles:
        lines.append("CAROUSEL TITLES USED:")
        lines += [f"  - {t}" for t in carousel_titles[-6:]]
        lines.append("")
    if save_mechs:
        lines.append("SAVE MECHANICS USED (use a different mechanic today):")
        lines += [f"  - {m}" for m in save_mechs[-4:]]
        lines.append("")
    if li_angles:
        lines.append("LINKEDIN ANGLES USED (use a completely different POV):")
        lines += [f"  - {a}" for a in li_angles[-4:]]
    return "\n".join(lines)
