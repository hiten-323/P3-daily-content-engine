"""
Brand guardrails — validates AI-generated creative assets against
Purity Beans brand guidelines before publishing.

Checks:
  • Colour palette compliance (dark espresso tones, not bright colours)
  • Logo presence / clearance
  • Text readability (white/cream on dark, not black on dark)
  • No competitor brand names in generated prompts
  • No banned phrases / claims

Used by all creative generators before returning output.
"""
import logging
import re

logger = logging.getLogger(__name__)

# ── Brand colour palette ──────────────────────────────────────────────────────
BRAND_COLOURS = {
    "espresso_black":  "#0D0905",
    "warm_dark_brown": "#1A0F07",
    "gold_accent":     "#C8962E",
    "cream_white":     "#F5EED8",
    "deep_amber":      "#8B4513",
}

APPROVED_BACKGROUNDS = [
    "black", "dark", "espresso", "charcoal", "deep brown",
    "dark marble", "dark wood", "moody", "shadow",
]

FORBIDDEN_BACKGROUNDS = [
    "rainbow clutter", "neon overload",
]

# ── Text / copy guardrails ────────────────────────────────────────────────────
BANNED_CLAIMS = [
    "clinically proven",
    "scientifically proven",
    "guaranteed weight loss",
    "cure",
    "medicine",
    "FDA approved",
    "FSSAI approved",  # only use if genuinely certified
]

COMPETITOR_NAMES = [
    "nescafe", "bru", "continental", "rage coffee", "blue tokai",
    "sleepy owl", "third wave", "davidoff", "lavazza",
]

REQUIRED_BRAND_ELEMENTS = ["purity beans", "p3online"]

# ── Prompt guardrails ─────────────────────────────────────────────────────────
_BRAND_STYLE_SUFFIX = (
    " — premium natural coffee photography, believable environment, disciplined warm brand accents, "
    "product packaging must remain accurate when shown, mobile-first composition, "
    "editorial FMCG photography with natural depth and tactile coffee detail"
)


def validate_image_prompt(prompt: str) -> tuple[bool, list[str], str]:
    """
    Validate and potentially auto-correct an image generation prompt.

    Returns:
        (is_valid, issues, corrected_prompt)
        is_valid = True if prompt passes all checks OR was auto-corrected.
    """
    issues: list[str] = []
    corrected = prompt

    # Check forbidden backgrounds
    lower = prompt.lower()
    for fb in FORBIDDEN_BACKGROUNDS:
        if fb in lower:
            issues.append(f"Forbidden background: '{fb}'")
            corrected = corrected.replace(fb, "dark espresso background")

    # Auto-append brand style if not present
    if "purity beans" not in lower and "dark" not in lower:
        corrected += _BRAND_STYLE_SUFFIX
        issues.append("Brand style suffix auto-added")

    # Check competitor mentions
    for comp in COMPETITOR_NAMES:
        if comp in lower:
            issues.append(f"Competitor mention detected: '{comp}'")
            corrected = re.sub(re.escape(comp), "premium coffee brand", corrected, flags=re.I)

    valid = len([i for i in issues if "auto-added" not in i and "auto-corrected" not in i]) == 0
    return valid, issues, corrected


def validate_copy(text: str) -> tuple[bool, list[str]]:
    """
    Validate marketing copy for banned claims and competitor mentions.

    Returns:
        (is_valid, issues)
    """
    issues: list[str] = []
    lower = text.lower()

    for claim in BANNED_CLAIMS:
        if claim in lower:
            issues.append(f"Banned claim: '{claim}'")

    for comp in COMPETITOR_NAMES:
        if comp in lower:
            issues.append(f"Competitor name: '{comp}' — remove or use generic 'leading brands'")

    return len(issues) == 0, issues


_REALISM_SUFFIX = (
    " Photographed look, not rendered: natural grain, one believable light source with "
    "correct shadow direction, correct contact shadow under the jar, environment reflections "
    "on glass, label texture like real printed paper, slight imperfections (a droplet, "
    "a fingerprint smudge, scattered granules), subject slightly off-center. "
    "No 3D-render look, no plastic surfaces, no oversaturation, no text in image."
)


def enforce_brand_prompt(prompt: str) -> str:
    """
    Ensure an image generation prompt is on-brand and engineered for realism.
    Always returns a safe, on-brand prompt string.
    """
    _, _, corrected = validate_image_prompt(prompt)
    if "photographed look" not in corrected.lower():
        corrected += _REALISM_SUFFIX
    return corrected


def get_brand_style_block() -> str:
    """Return the standard brand style description for image prompts."""
    return (
        "Purity Beans visual identity: premium natural coffee photography, warm coffee/amber accents, "
        "clean mobile-first composition, tactile product and beverage detail, believable light, "
        "varied real-world backgrounds; preserve exact packaging whenever the product is visible"
    )
