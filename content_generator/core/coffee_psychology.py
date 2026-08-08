
"""
Coffee Marketing Psychology — single source of truth for Purity Beans content.
"""
from __future__ import annotations
import logging
import re

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
                "The bitter truth about your sweet morning coffee.",
                "Why your instant coffee does not smell like a café."
            ],
            "best_formats": ["reel", "carousel"],
            "share_trigger": "Tag the person who buys the big cheap jars."
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
                "Rituals increase enjoyment and willingness to pay. Framing the daily "
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
                "Sensory memory is sticky. Describing the exact moment the taste "
                "changes (bitterness at minute two, muddy aftertaste, missing aroma) "
                "gives the viewer a private test they can run tomorrow morning."
            )
        },
        "creative_application": {
            "example_hooks": [
                "It tastes bitter after two minutes. That is not normal.",
                "Real coffee does not leave a muddy aftertaste.",
                "The first sip that finally tastes like coffee."
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
                "People share content that improves their status inside their circle. "
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
            "core": "Café quality without café price or café effort.",
            "why_it_works": (
                "Resolves the price-sensitivity paradox. Urban Indians will pay for "
                "quality when friction is removed. Instant + pure + Rs 18/cup is the "
                "sweet spot — premium feeling, everyday accessible."
            )
        },
        "creative_application": {
            "example_hooks": [
                "Rs 18. Same purity the café charges Rs 180 for.",
                "Real coffee does not require a machine or a weekend.",
                "Premium is not the price. Premium is what is missing from the jar."
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
                "Premium choice is often rational uncertainty management, not status. "
                "'I know what I am drinking' is a stronger closer than 'this is better'."
            )
        },
        "creative_application": {
            "example_hooks": [
                "The only claim that matters: nothing is hiding in this jar.",
                "You should not need a chemistry degree to trust your coffee.",
                "100% coffee. Zero chicory. Written so you can verify it."
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
    return FRAMES_BY_ID.get(frame_id)

def frame_prompt_block() -> str:
    lines = [
        "PSYCHOLOGY FRAMES (pick ONE primary frame for this asset — do not invent a new one):",
    ]
    for f in PSYCHOLOGY_FRAMES:
        lines.append(f"PSYCHOLOGY FRAME")
        lines.append(f"Name: {f['name']}")
        lines.append(f"Risk: {f['risk_level'].title()}")
        lines.append("")
        lines.append("BEHAVIORAL PRINCIPLE")
        lines.append(f"Core Theory: {f['theory']['core']}")
        lines.append(f"Why it works: {f['theory']['why_it_works']}")
        lines.append("")
        lines.append("CREATIVE APPLICATION")
        lines.append(f"Share Trigger: {f['creative_application']['share_trigger']}")
        lines.append(f"Example Hooks (MECHANISMS ONLY, DO NOT COPY AS FACTUAL CLAIMS):")
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

    lines.append("MANDATORY TRUTH RULES")
    lines.append("HIGHEST PRIORITY")
    lines.append("1. Verified brand/product facts")
    lines.append("2. Brand safety policy")
    lines.append("3. Psychology governance")
    lines.append("4. Creative strategy")
    lines.append("5. Virality optimization")
    lines.append("LOWEST PRIORITY")
    lines.append("")
    lines.append("If a creative or psychological objective conflicts with a verified fact or safety rule, abandon the creative objective.")
    lines.append("- Never invent statistics.")
    lines.append("- Never infer competitor facts.")
    lines.append("- Never convert an example into a factual claim.")
    lines.append("- Never create an offer that is not active.")
    lines.append("- Verified product facts must come from the product knowledge source.")
    lines.append("")
    lines.append("MANDATORY GOVERNANCE RULE: The chosen psychological mechanism must never override truthfulness.")
    lines.append("Verified facts and brand policies always supersede psychological triggers. Do not fabricate")
    lines.append("statistics or competitor claims to increase shock value.")
    lines.append("The chosen frame must shape the hook, the emotional arc, and the share/save trigger.")

    return "\n".join(lines)


def recommended_frame_for_format(fmt: str) -> list[str]:
    fmt = (fmt or "").lower()
    out = []
    for f in PSYCHOLOGY_FRAMES:
        if fmt in f["creative_application"]["best_formats"]:
            out.append(f["id"])
    return out or [f["id"] for f in PSYCHOLOGY_FRAMES]


def validate_registry() -> bool:
    seen_ids = set()
    valid_risk_levels = {"low", "medium", "high"}
    id_pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    
    for f in PSYCHOLOGY_FRAMES:
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
                
    logger.info("[psychology] All %d psychology frames verified successfully against the strict registry schema.", len(PSYCHOLOGY_FRAMES))
    return True

validate_registry()
