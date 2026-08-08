
"""
Coffee Marketing Psychology — single source of truth for Purity Beans content.
"""
from __future__ import annotations
import logging
import re
from copy import deepcopy

logger = logging.getLogger(__name__)

PSYCHOLOGY_SCHEMA_VERSION = 2
VALID_OBJECTIVES = {"shareability", "saves", "comments", "follows", "trust", "education", "conversion"}
VALID_FORMATS = {"reel", "carousel", "story"}

PSYCHOLOGY_FRAMES = [
    {
        "id": "revelation",
        "name": "Revelation / Cognitive Dissonance",
        "version": 1,
        "objective": "comments",
        "risk_level": "medium",
        "theory": {
            "core": "You have been drinking something that is not what you thought it was.",
            "why_it_works": (
                "Creates immediate dissonance. The viewer must either defend the old "
                "habit or update it. Either response is engagement."
            )
        },
        "creative_application": {
            "example_hooks": [
                "Your coffee label may not tell the story you think it does.",
                "Check this one line before you buy your next coffee.",
                "What is actually in your instant coffee?"
            ],
            "best_formats": ["reel", "carousel"],
            "share_trigger": "Share with someone who always assumes instant coffee is exactly the same as café coffee."
        },
        "governance": {
            "allowed_claim_categories": ["ingredient_label_education", "chicory_vs_coffee_composition", "verified_product_composition"],
            "prohibited_claims": ["chicory is toxic", "chicory causes health issues"]
        }
    },
    {
        "id": "ritual_identity",
        "name": "Ritual Identity",
        "version": 1,
        "objective": "trust",
        "risk_level": "low",
        "theory": {
            "core": "The morning cup is not caffeine delivery. It is the first decision of the day.",
            "why_it_works": (
                "Hypothesis: Rituals increase enjoyment and willingness to pay. Framing the daily "
                "cup as identity ('I choose pure') makes switching feel like an upgrade "
                "to the self, not just the product."
            )
        },
        "creative_application": {
            "example_hooks": [
                "Your morning routine sets the tone for your day.",
                "Upgrade your first decision today.",
                "A better morning starts with a pure cup."
            ],
            "best_formats": ["reel", "story"],
            "share_trigger": "Share with someone who values their morning quiet time."
        },
        "governance": {
            "allowed_claim_categories": ["product_aroma", "manufacturing_quality", "sensory_experience"],
            "prohibited_claims": ["guarantees a productive day", "medical mood enhancement"]
        }
    },
    {
        "id": "sensory_contrast",
        "name": "Sensory Contrast",
        "version": 1,
        "objective": "saves",
        "risk_level": "medium",
        "theory": {
            "core": "Once you notice the muddy aftertaste of chicory, you cannot un-taste it.",
            "why_it_works": (
                "Hypothesis: Sensory memory is sticky. Describing the exact moment the taste "
                "changes (bitterness at minute two, muddy aftertaste, missing aroma) "
                "gives the viewer a private test they can run tomorrow morning."
            )
        },
        "creative_application": {
            "example_hooks": [
                "Notice what happens to the taste after your first few sips.",
                "Pay attention to the aftertaste of your regular cup.",
                "Compare the aroma of your current jar to a fresh café pour."
            ],
            "best_formats": ["reel", "carousel"],
            "share_trigger": "Share with the person who always says 'coffee just tastes bitter'."
        },
        "governance": {
            "allowed_claim_categories": ["taste_comparison", "aroma_differences", "aftertaste_education"],
            "prohibited_claims": ["pure coffee is sweet without sugar", "sensory preferences are absolute medical health signals"]
        }
    },
    {
        "id": "social_currency",
        "name": "Social Currency / Shareable Discovery",
        "version": 1,
        "objective": "shareability",
        "risk_level": "medium",
        "theory": {
            "core": "This is information that makes the sharer look informed.",
            "why_it_works": (
                "Hypothesis: People share content that improves their status inside their circle. "
                "'3 signs...', 'look at the label', 'what the ingredient panel actually "
                "says' are high-status discoveries. Product shots are not."
            )
        },
        "creative_application": {
            "example_hooks": [
                "Show this to anyone who still buys the big jar without checking.",
                "The one line on the label that changes everything.",
                "What every coffee lover in your office needs to see."
            ],
            "best_formats": ["carousel", "reel"],
            "share_trigger": "Forward this to the friend who buys coffee for the whole office."
        },
        "governance": {
            "allowed_claim_categories": ["ingredient_transparency", "consumer_education", "label_reading"],
            "prohibited_claims": ["anyone drinking chicory is stupid", "unverified status shaming"]
        }
    },
    {
        "id": "accessible_premium",
        "name": "Accessible Premium",
        "version": 1,
        "objective": "conversion",
        "risk_level": "low",
        "theory": {
            "core": "Premium quality without the typical friction or expense.",
            "why_it_works": (
                "Hypothesis: Resolves the price-sensitivity paradox. Urban Indians will pay for "
                "quality when friction is removed. Accessible premium positioning serves as the "
                "sweet spot — premium feeling, everyday accessible."
            )
        },
        "creative_application": {
            "example_hooks": [
                "What if premium coffee didn't require a café?",
                "Consider the actual cost of your daily café habit.",
                "You don't need a machine to upgrade your morning."
            ],
            "best_formats": ["reel", "carousel", "story"],
            "share_trigger": "Send this to anyone who thinks pure coffee has to be expensive."
        },
        "governance": {
            "allowed_claim_categories": ["serving_economics", "cafe_price_comparison", "value_proposition"],
            "prohibited_claims": ["cafe coffee is unhealthy", "unverified price calculations"]
        }
    },
    {
        "id": "certainty",
        "name": "Loss Aversion / Certainty",
        "version": 1,
        "objective": "trust",
        "risk_level": "medium",
        "theory": {
            "core": "Knowing exactly what is in the cup removes a quiet daily uncertainty.",
            "why_it_works": (
                "Hypothesis: Premium choice is often rational uncertainty management, not status. "
                "'I know what I am drinking' is a stronger closer than 'this is better'."
            )
        },
        "creative_application": {
            "example_hooks": [
                "Read the ingredient line before you decide.",
                "You shouldn't have to guess what's in your cup.",
                "Transparency is the only label that matters."
            ],
            "best_formats": ["carousel", "reel"],
            "share_trigger": "Save this if you are tired of guessing what is in your cup."
        },
        "governance": {
            "allowed_claim_categories": ["brand_transparency", "ingredient_purity", "verified_composition"],
            "prohibited_claims": ["non-labeled foods cause cancer", "other coffee brands are illegal or toxic"]
        }
    }
]

# Fast lookup
FRAMES_BY_ID = {f["id"]: f for f in PSYCHOLOGY_FRAMES}

def get_frame(frame_id: str) -> dict | None:
    frame = FRAMES_BY_ID.get(frame_id)
    if not frame:
        return None

    # Return a deep copy with operational metadata attached so it can be enforced without mutating registry
    frame_copy = deepcopy(frame)
    risk = frame_copy["risk_level"]
    frame_copy["governance_rules"] = {
        "risk_level": risk,
        "require_claim_verification": risk in ("medium", "high"),
        "require_source_backing": risk == "high",
        "require_manual_review": risk == "high"
    }
    return frame_copy

def _render_truth_rules() -> list[str]:
    return [
        "MANDATORY TRUTH RULES",
        "HIGHEST PRIORITY",
        "1. Verified brand/product facts",
        "2. Brand safety policy",
        "3. Psychology governance",
        "4. Creative strategy",
        "5. Virality optimization",
        "LOWEST PRIORITY",
        "",
        "If a creative or psychological objective conflicts with a verified fact or safety rule, abandon the creative objective.",
        "- Never invent statistics.",
        "- Never infer competitor facts.",
        "- Never convert an example into a factual claim.",
        "- Never create an offer that is not active.",
        "- Verified product facts must come from the product knowledge source.",
        "",
        "MANDATORY GOVERNANCE RULE: The chosen psychological mechanism must never override truthfulness.",
        "Verified facts and brand policies always supersede psychological triggers. Do not fabricate",
        "statistics or competitor claims to increase shock value.",
        "The chosen frame must shape the hook, the emotional arc, and the share/save trigger."
    ]

def get_frame_selection_context() -> str:
    """Context block exposing all psychology frames strictly for the Growth Director to select from."""
    lines = [
        "PSYCHOLOGY FRAMES (Select ONE primary frame to drive the content strategy):",
        ""
    ]
    for f in PSYCHOLOGY_FRAMES:
        lines.append(f"[{f['id']}] {f['name']} (Risk Level: {f['risk_level'].title()})")
        lines.append(f"  Core Theory: {f['theory']['core']}")
        lines.append(f"  Why it works: {f['theory']['why_it_works']}")
        lines.append(f"  Objective: {f['objective']}")
        lines.append("")

    lines.extend(_render_truth_rules())
    return "\n".join(lines)

def frame_prompt_block(frame_id: str) -> str:
    """Generates the content generation prompt block for ONE specific frame."""
    if not frame_id or frame_id not in FRAMES_BY_ID:
        raise ValueError(f"Invalid or missing frame_id: {frame_id}")

    f = FRAMES_BY_ID[frame_id]
    lines = [
        f"PRIMARY PSYCHOLOGY FRAME: {f['name']}",
        f"Risk: {f['risk_level'].title()}",
        "",
        "BEHAVIORAL PRINCIPLE",
        f"Core Theory: {f['theory']['core']}",
        f"Why it works: {f['theory']['why_it_works']}",
        "",
        "CREATIVE APPLICATION",
        f"Share Trigger: {f['creative_application']['share_trigger']}",
        f"Example Hooks (MECHANISMS ONLY, DO NOT COPY AS FACTUAL CLAIMS):"
    ]
    for hook in f['creative_application']['example_hooks']:
        lines.append(f"  - {hook}")
    lines.append(f"Best Formats: {', '.join(f['creative_application']['best_formats'])}")
    lines.append("")
    lines.append("GOVERNANCE")
    lines.append(f"Allowed claim categories:")
    lines.append(f"  {', '.join(f['governance']['allowed_claim_categories'])}")
    lines.append(f"Prohibited:")
    lines.append(f"  {', '.join(f['governance']['prohibited_claims'])}")

    # Operational Risk - enforce stricter generation behavior
    if f['risk_level'] in ('medium', 'high'):
        lines.append("WARNING (MEDIUM/HIGH RISK FRAME): Explicit claim verification required. Do not imply unsupported facts.")
    if f['risk_level'] == 'high':
        lines.append("WARNING (HIGH RISK FRAME): Source-backed facts and strict safety validation required. Manual approval may be enforced.")

    lines.append("-" * 40)
    lines.append("")

    lines.extend(_render_truth_rules())

    return "\n".join(lines)


def recommended_frame_for_format(fmt: str) -> list[str]:
    fmt = (fmt or "").lower()
    if fmt not in VALID_FORMATS:
        raise ValueError(f"Invalid format requested: {fmt}. Must be one of {VALID_FORMATS}")
    out = []
    for f in PSYCHOLOGY_FRAMES:
        if fmt in f["creative_application"]["best_formats"]:
            out.append(f["id"])
    return out


def validate_registry(frames: list[dict] = None) -> bool:
    frames = frames if frames is not None else PSYCHOLOGY_FRAMES
    seen_ids = set()
    valid_risk_levels = {"low", "medium", "high"}
    id_pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    
    for f in frames:
        expected_keys = {"id", "name", "version", "objective", "risk_level", "theory", "creative_application", "governance"}
        for key in expected_keys:
            if key not in f:
                raise ValueError(f"Psychology frame missing required root key: '{key}' in frame: {f.get('id', 'unknown')}")
        unexpected_keys = set(f.keys()) - expected_keys
        if unexpected_keys:
            raise ValueError(f"Unexpected top-level fields in frame '{f.get('id', 'unknown')}': {unexpected_keys}")
        
        f_id = f["id"]
        if not isinstance(f_id, str) or not f_id:
            raise ValueError(f"Invalid frame ID: {f_id}")
        if not id_pattern.match(f_id):
            raise ValueError(f"Invalid frame ID format (must match ^[a-z][a-z0-9_]*$): '{f_id}'")
        if f_id in seen_ids:
            raise ValueError(f"Duplicate psychology frame ID detected: '{f_id}'")
        seen_ids.add(f_id)
        
        name = f["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"name must be a non-empty string in frame '{f_id}'")

        if not isinstance(f["version"], int) or f["version"] < 1:
            raise ValueError(f"version must be a positive integer in frame '{f_id}'")

        objective = f["objective"]
        if objective not in VALID_OBJECTIVES:
            raise ValueError(f"Invalid objective '{objective}' in frame '{f_id}'. Must be one of {VALID_OBJECTIVES}")

        risk = f["risk_level"]
        if risk not in valid_risk_levels:
            raise ValueError(f"Invalid risk_level '{risk}' in frame '{f_id}'. Must be one of {valid_risk_levels}")
            
        theory = f["theory"]
        if not isinstance(theory, dict):
            raise ValueError(f"theory must be a dict in frame '{f_id}'")
        theory_expected_keys = {"core", "why_it_works"}
        for key in theory_expected_keys:
            if key not in theory or not isinstance(theory[key], str) or not theory[key].strip():
                raise ValueError(f"theory block missing or has empty key '{key}' in frame '{f_id}'")
        theory_unexpected_keys = set(theory.keys()) - theory_expected_keys
        if theory_unexpected_keys:
            raise ValueError(f"Unexpected fields in theory block in frame '{f_id}': {theory_unexpected_keys}")
                
        creative = f["creative_application"]
        if not isinstance(creative, dict):
            raise ValueError(f"creative_application must be a dict in frame '{f_id}'")
        creative_expected_keys = {"example_hooks", "share_trigger", "best_formats"}
        for key in creative_expected_keys:
            if key not in creative:
                raise ValueError(f"creative_application missing key '{key}' in frame '{f_id}'")
        creative_unexpected_keys = set(creative.keys()) - creative_expected_keys
        if creative_unexpected_keys:
            raise ValueError(f"Unexpected fields in creative_application block in frame '{f_id}': {creative_unexpected_keys}")
        
        if not isinstance(creative["example_hooks"], list) or len(creative["example_hooks"]) == 0 or not all(isinstance(x, str) and x.strip() for x in creative["example_hooks"]):
            raise ValueError(f"example_hooks must be a non-empty list of non-empty strings in frame '{f_id}'")
            
        if not isinstance(creative["share_trigger"], str) or not creative["share_trigger"].strip():
            raise ValueError(f"share_trigger must be a non-empty string in frame '{f_id}'")
            
        if not isinstance(creative["best_formats"], list) or len(creative["best_formats"]) == 0 or not all(isinstance(x, str) for x in creative["best_formats"]):
            raise ValueError(f"best_formats must be a non-empty list of strings in frame '{f_id}'")
        for fmt in creative["best_formats"]:
            if fmt not in VALID_FORMATS:
                raise ValueError(f"Invalid format '{fmt}' in best_formats in frame '{f_id}'. Must be one of {VALID_FORMATS}")

        gov = f["governance"]
        if not isinstance(gov, dict):
            raise ValueError(f"governance must be a dict in frame '{f_id}'")
        gov_expected_keys = {"allowed_claim_categories", "prohibited_claims"}
        for key in gov_expected_keys:
            if key not in gov:
                raise ValueError(f"governance missing key '{key}' in frame '{f_id}'")
            if not isinstance(gov[key], list) or not all(isinstance(x, str) and x.strip() for x in gov[key]):
                raise ValueError(f"{key} must be a list of non-empty strings in frame '{f_id}'")
        gov_unexpected_keys = set(gov.keys()) - gov_expected_keys
        if gov_unexpected_keys:
            raise ValueError(f"Unexpected fields in governance block in frame '{f_id}': {gov_unexpected_keys}")

        # Operational check: high risk requires stricter validation rules implicitly
        if risk == "high":
            if len(gov["prohibited_claims"]) == 0:
                raise ValueError(f"High risk frame '{f_id}' must specify prohibited_claims")
                
    logger.info("[psychology] All %d psychology frames verified successfully against the strict registry schema.", len(frames))
    return True

SUPPORTED_SCHEMA_VERSION = 2
if PSYCHOLOGY_SCHEMA_VERSION != SUPPORTED_SCHEMA_VERSION:
    raise ValueError(f"Unsupported schema version: {PSYCHOLOGY_SCHEMA_VERSION}")

validate_registry()
# Make registry effectively immutable at runtime
PSYCHOLOGY_FRAMES = tuple(PSYCHOLOGY_FRAMES)
