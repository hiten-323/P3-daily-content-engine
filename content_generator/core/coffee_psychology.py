"""
Coffee Marketing Psychology — single source of truth for Purity Beans content.

Why this exists:
  Generic "premium coffee" language produces advertisements. People do not share
  advertisements. The content that travels is the thing someone sends a friend —
  the revelation, the label test, the sensory difference after years of filler.

  These frames are ranked by fit for a pure-instant brand in India. Every
  generation prompt should pick one (or a clean combination) rather than invent
  a new angle from scratch.

Evidence base (condensed):
  - Ritual communication raises willingness-to-pay (Intellect 2023).
  - Revelation / cognitive dissonance is the strongest pure-coffee lever in India
    (chicory normalised for decades; FSSAI front-of-pack rules make it timely).
  - Clean-label self-signaling is rising among urban 25-40s who already read
    ingredient panels on other categories.
  - Social currency ("3 signs…", "look at the label") drives saves + shares more
    reliably than product shots.
  - Accessible premium (café quality at home price) resolves the price-sensitivity
    paradox without status anxiety.
"""
from __future__ import annotations

# ── Primary frames (ordered by leverage for this brand) ───────────────────────

PSYCHOLOGY_FRAMES = [
    {
        "id": "revelation",
        "name": "Revelation / Cognitive Dissonance",
        "core": "You have been drinking something that is not what you thought it was.",
        "why_it_works": (
            "Creates immediate dissonance. The viewer must either defend the old "
            "habit or update it. Either response is engagement."
        ),
        "example_hooks": [
            "You have been drinking chicory your entire life.",
            "Most people do not know their daily coffee has filler.",
            "What is actually inside your coffee jar?",
        ],
        "best_formats": ["reel", "carousel"],
        "share_trigger": "Tag the person who still buys the big brand without reading the label.",
    },
    {
        "id": "clean_label",
        "name": "Clean-Label Self-Signaling",
        "core": "Reading the label is an act of self-respect, not paranoia.",
        "why_it_works": (
            "Turns a low-effort behaviour (looking at the back of the pack) into "
            "an identity signal. The person who checks becomes the informed one."
        ),
        "example_hooks": [
            "3 signs your coffee is not pure.",
            "How to read a coffee label in 15 seconds.",
            "The ingredient most brands hope you never notice.",
        ],
        "best_formats": ["carousel", "reel"],
        "share_trigger": "Save this before your next grocery run.",
    },
    {
        "id": "ritual",
        "name": "Ritual Elevation",
        "core": "The morning cup is not caffeine delivery. It is the first decision of the day.",
        "why_it_works": (
            "Rituals increase enjoyment and willingness to pay. Framing the daily "
            "cup as identity ("I choose pure") makes switching feel like an upgrade "
            "to the self, not just the product."
        ),
        "example_hooks": [
            "Your morning coffee is the first decision you make about yourself.",
            "Start the day with something that is actually coffee.",
            "The 2-minute ritual that changes the rest of the day.",
        ],
        "best_formats": ["reel", "story"],
        "share_trigger": "Send this to someone who still starts the day on autopilot.",
    },
    {
        "id": "sensory",
        "name": "Sensory Contrast",
        "core": "Once you taste real coffee, the filler version becomes obvious.",
        "why_it_works": (
            "Sensory memory is sticky. Describing the exact moment the taste "
            "changes (bitterness at minute two, muddy aftertaste, missing aroma) "
            "gives the viewer a private test they can run tomorrow morning."
        ),
        "example_hooks": [
            "It tastes bitter after two minutes. That is not normal.",
            "Real coffee does not leave a muddy aftertaste.",
            "The first sip that finally tastes like coffee.",
        ],
        "best_formats": ["reel", "carousel"],
        "share_trigger": "Share with the person who always says "coffee just tastes bitter".",
    },
    {
        "id": "social_currency",
        "name": "Social Currency / Shareable Discovery",
        "core": "This is information that makes the sharer look informed.",
        "why_it_works": (
            "People share content that improves their status inside their circle. "
            ""3 signs…", "look at the label", "what the ingredient panel actually "
            "says" are high-status discoveries. Product shots are not."
        ),
        "example_hooks": [
            "Show this to anyone who still buys the big jar without checking.",
            "The one line on the label that changes everything.",
            "What every coffee lover in your office needs to see.",
        ],
        "best_formats": ["carousel", "reel"],
        "share_trigger": "Forward this to the friend who buys coffee for the whole office.",
    },
    {
        "id": "accessible_premium",
        "name": "Accessible Premium",
        "core": "Café quality without café price or café effort.",
        "why_it_works": (
            "Resolves the price-sensitivity paradox. Urban Indians will pay for "
            "quality when friction is removed. Instant + pure + Rs 18/cup is the "
            "sweet spot — premium feeling, everyday accessible."
        ),
        "example_hooks": [
            "Rs 18. Same purity the café charges Rs 180 for.",
            "Real coffee does not require a machine or a weekend.",
            "Premium is not the price. Premium is what is missing from the jar.",
        ],
        "best_formats": ["reel", "carousel", "story"],
        "share_trigger": "Send this to anyone who thinks pure coffee has to be expensive.",
    },
    {
        "id": "certainty",
        "name": "Loss Aversion / Certainty",
        "core": "Knowing exactly what is in the cup removes a quiet daily uncertainty.",
        "why_it_works": (
            "Premium choice is often rational uncertainty management, not status. "
            ""I know what I am drinking" is a stronger closer than "this is better"."
        ),
        "example_hooks": [
            "The only claim that matters: nothing is hiding in this jar.",
            "You should not need a chemistry degree to trust your coffee.",
            "100% coffee. Zero chicory. Written so you can verify it.",
        ],
        "best_formats": ["carousel", "reel"],
        "share_trigger": "Save this if you are tired of guessing what is in your cup.",
    },
]

# Fast lookup
FRAMES_BY_ID = {f["id"]: f for f in PSYCHOLOGY_FRAMES}


def get_frame(frame_id: str) -> dict | None:
    return FRAMES_BY_ID.get(frame_id)


def frame_prompt_block() -> str:
    """
    Compact block injected into generation prompts.
    Forces the model to pick one primary frame instead of inventing angles.
    """
    lines = [
        "PSYCHOLOGY FRAMES (pick ONE primary frame for this asset — do not invent a new one):",
    ]
    for f in PSYCHOLOGY_FRAMES:
        lines.append(
            f"  [{f['id']}] {f['name']}: {f['core']}"
        )
    lines.append(
        "The chosen frame must shape the hook, the emotional arc, and the share/save trigger. "
        "Product claims (100% coffee, zero chicory, Rs 18/cup) support the frame — they are not the frame."
    )
    return "\n".join(lines)


def recommended_frame_for_format(fmt: str) -> list[str]:
    """Return frame ids that historically fit a given format."""
    fmt = (fmt or "").lower()
    out = []
    for f in PSYCHOLOGY_FRAMES:
        if fmt in f["best_formats"]:
            out.append(f["id"])
    return out or [f["id"] for f in PSYCHOLOGY_FRAMES]
