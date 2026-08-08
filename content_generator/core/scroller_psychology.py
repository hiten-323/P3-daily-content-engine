"""
Scroller psychology — why someone stops scrolling.

Distinct from coffee_psychology, which answers why someone cares, shares or
buys. Kept as separate registries on purpose (ADR-002): attention and meaning
are different decisions, and merging them produces a hook bank rather than a
model of viewer behaviour.

    Scroller psychology  ->  "Why would someone stop?"
    Coffee psychology    ->  "Why would someone share/save/follow/buy?"

SCOPE OF THIS FILE (ADR-002 Phases 1-2)
  It CLASSIFIES what a piece of content actually does, and enforces that a
  curiosity mechanism is paid off. It does not yet SELECT a mechanism before
  generation — that is Phase 4, and it is deliberately held until measurement
  is confirmed working, because a selection layer that cannot be evaluated is
  a more elaborate guess.

  Classification-now/selection-later is the honest ordering: it starts
  accumulating the data Phase 4 needs to be worth anything, without pretending
  we already know which mechanism wins.

NO "default" MECHANISM. Classification returns "" when it cannot tell, and ""
is recorded as unknown rather than smuggled in as a real value — the same rule
that governs psychology frames.
"""
from __future__ import annotations
import logging
import re

logger = logging.getLogger(__name__)

# Each entry describes an actual viewer behaviour, not a copywriting trick.
# `payoff_requirement` is what the viewer must RECEIVE for the mechanism to be
# honest — an open loop with nothing behind it is bait.
MECHANISMS: list[dict] = [
    {"id": "pattern_interrupt", "name": "Pattern interrupt",
     "description": "Breaks the visual or verbal rhythm of the feed.",
     "payoff_requirement": "the interruption must lead somewhere, not just startle",
     "signals": ("stop", "wait", "actually", "no one", "nobody", "never")},
    {"id": "curiosity_gap", "name": "Curiosity gap",
     "description": "Names a specific thing the viewer does not know.",
     "payoff_requirement": "the gap must be closed inside the same asset",
     "signals": ("what", "why", "how", "the reason", "turns out", "difference")},
    {"id": "open_loop", "name": "Open loop",
     "description": "Starts something the viewer needs finished.",
     "payoff_requirement": "the loop must close before the asset ends",
     "signals": ("until", "before you", "next time", "then", "watch what")},
    {"id": "recognition", "name": "Recognition",
     "description": "Viewer sees their own experience described.",
     "payoff_requirement": "must explain the experience, not merely name it",
     "signals": ("you know when", "ever", "every morning", "we all", "your")},
    {"id": "surprise", "name": "Surprise",
     "description": "A true fact that contradicts an assumption.",
     "payoff_requirement": "the surprising claim must be verifiable",
     "signals": ("isn't", "is not", "wrong", "myth", "actually", "not really")},
    {"id": "useful_discovery", "name": "Useful discovery",
     "description": "Something the viewer can use immediately.",
     "payoff_requirement": "must be actionable without buying anything",
     "signals": ("check", "read the label", "test", "try", "look for", "compare")},
    {"id": "identity_signal", "name": "Identity signal",
     "description": "Says something about the kind of person the viewer is.",
     "payoff_requirement": "must be earned, not flattery",
     "signals": ("if you", "people who", "real coffee", "serious about")},
    {"id": "tension_resolution", "name": "Tension and resolution",
     "description": "Sets up a problem, then resolves it.",
     "payoff_requirement": "the resolution must be shown, not promised",
     "signals": ("problem", "but", "however", "the fix", "instead", "solution")},
    {"id": "specificity", "name": "Specificity",
     "description": "A concrete detail that proves first-hand knowledge.",
     "payoff_requirement": "the detail must be checkable",
     "signals": ("seconds", "minutes", "gram", "label", "ingredient", "rs ")},
    {"id": "social_currency", "name": "Social currency",
     "description": "Worth repeating because it makes the sharer look informed.",
     "payoff_requirement": "must give the sharer something to say",
     "signals": ("most people", "nobody tells", "little known", "insider")},
    {"id": "proof", "name": "Proof",
     "description": "Demonstrates rather than asserts.",
     "payoff_requirement": "the demonstration must be visible",
     "signals": ("watch", "see", "side by side", "here is", "look at", "shows")},
]
MECHANISMS_BY_ID = {m["id"]: m for m in MECHANISMS}

# Viewer states. Each needs a different opening move; using one mechanism for
# every asset is what makes a feed monotonous.
STATES: list[dict] = [
    {"id": "uninterested", "needs": "pattern interruption"},
    {"id": "curious",      "needs": "a clear unanswered question"},
    {"id": "skeptical",    "needs": "proof"},
    {"id": "busy",         "needs": "immediate utility"},
    {"id": "identity_seeking", "needs": "self-recognition"},
    {"id": "informed",     "needs": "a new discovery"},
    {"id": "ready_to_buy", "needs": "trust and reduced friction"},
]
STATES_BY_ID = {s["id"]: s for s in STATES}

_STATE_FOR_MECHANISM = {
    "pattern_interrupt": "uninterested",
    "curiosity_gap": "curious",
    "open_loop": "curious",
    "recognition": "identity_seeking",
    "surprise": "informed",
    "useful_discovery": "busy",
    "identity_signal": "identity_seeking",
    "tension_resolution": "skeptical",
    "specificity": "skeptical",
    "social_currency": "identity_seeking",
    "proof": "skeptical",
}


def _copy_of(piece: dict) -> str:
    """All viewer-facing copy in one string."""
    if not isinstance(piece, dict):
        return ""
    parts = [str(piece.get(k) or "") for k in
             ("hook", "hook_text", "hook_spoken", "hook_text_overlay", "headline",
              "title", "caption", "body", "cta")]
    for lst in ("slides", "frames", "script", "scenes"):
        for item in (piece.get(lst) or []):
            if isinstance(item, dict):
                parts += [str(item.get(k) or "") for k in
                          ("heading", "headline", "body", "on_screen", "spoken", "voiceover")]
            elif isinstance(item, str):
                parts.append(item)
    return " ".join(parts).lower()


def classify_mechanism(piece: dict) -> str:
    """
    Which attention mechanism this copy actually uses.
    Returns "" when it cannot tell — never a placeholder id.
    """
    text = _copy_of(piece)
    if not text.strip():
        return ""
    scores = {m["id"]: sum(1 for s in m["signals"] if s in text) for m in MECHANISMS}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else ""


def classify_state(piece: dict) -> str:
    """The viewer state the copy is written for, derived from its mechanism."""
    mech = classify_mechanism(piece)
    return _STATE_FOR_MECHANISM.get(mech, "")


# ── Payoff (ADR-002 Phase 2) ─────────────────────────────────────────────────
#
# A curiosity mechanism with nothing behind it is bait, and nothing in the
# pipeline rejected it: a strong hook passed every gate even when the viewer
# learned nothing. Payoff is what separates a hook from a headline.

_PAYOFF_KINDS = {
    "new_knowledge":     ("because", "the reason", "turns out", "what happens",
                          "this means", "which is why", "the difference"),
    "useful_test":       ("check", "read the label", "test", "try this",
                          "look for", "next time you"),
    "comparison":        ("versus", " vs ", "side by side", "compared",
                          "difference between"),
    "decision_framework":("if it", "when it", "rule of thumb", "how to choose",
                          "what to look for"),
    "practical_action":  ("swap", "switch", "stop", "start", "add", "avoid"),
    "verified_discovery":("chicory", "ingredient", "label", "freeze dried",
                          "arabica", "robusta", "additives"),
}

# Copy that opens a loop. If one of these is present, a payoff is mandatory.
_OPENS_LOOP = re.compile(
    r"\b(most people|nobody|no one|what if|why|how|the reason|turns out|"
    r"you('| a)re (making|doing) .{0,20}wrong|isn'?t|is not|secret|hidden|"
    r"before you|until you|don'?t know)\b", re.I)


def payoff_strength(piece: dict) -> dict:
    """
    Does the viewer actually receive something?

    Returns {"score": 0-100, "kinds": [...], "opens_loop": bool,
             "passes": bool, "reason": str}

    The rule is proportional, not absolute: content that opens a loop must pay
    it off. Content that never opened one (a straight demonstration, say) is
    not penalised for having no reveal.
    """
    text = _copy_of(piece)
    if not text.strip():
        return {"score": 0.0, "kinds": [], "opens_loop": False, "passes": False,
                "reason": "no copy to judge"}

    kinds = [k for k, sigs in _PAYOFF_KINDS.items() if any(s in text for s in sigs)]
    opens = bool(_OPENS_LOOP.search(text))

    score = min(100.0, len(kinds) * 28.0)
    # Length is a weak proxy for whether anything was actually explained.
    if len(text.split()) < 12:
        score -= 20

    score = max(0.0, score)
    if opens and not kinds:
        return {"score": score, "kinds": kinds, "opens_loop": True, "passes": False,
                "reason": "opens a curiosity loop and never closes it — the viewer "
                          "learns nothing, which is the definition of bait"}
    if not kinds and not opens:
        return {"score": score, "kinds": kinds, "opens_loop": False, "passes": False,
                "reason": "delivers no knowledge, test, comparison or action"}
    return {"score": score, "kinds": kinds, "opens_loop": opens, "passes": True,
            "reason": f"pays off with: {', '.join(kinds)}"}


# ── Hook decomposition (ADR-002 Phase 3) ─────────────────────────────────────

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", str(s or "").lower()).strip()


def hook_layers(piece: dict) -> dict:
    """The three hook channels a video has, and whether they are distinct."""
    on_screen = _norm(piece.get("hook_text_overlay") or piece.get("hook_text"))
    spoken    = _norm(piece.get("hook_spoken"))
    visual    = _norm(piece.get("hook_visual_concept") or piece.get("visual_hook"))
    present   = {k: v for k, v in
                 (("on_screen", on_screen), ("spoken", spoken), ("visual", visual)) if v}
    distinct  = len({v for v in present.values()}) == len(present)
    return {"layers": present, "distinct": distinct}


def check_hook_decomposition(piece: dict) -> dict:
    """
    A reel's on-screen text, spoken line and visual should do different work.
    Repeating one sentence across all three wastes the only seconds that decide
    whether the viewer stays.

    Only enforced when at least two channels are present — an asset that simply
    has no separate spoken hook is not penalised here.
    """
    info = hook_layers(piece)
    layers = info["layers"]
    if len(layers) < 2:
        return {"passes": True, "reason": "fewer than two hook channels present"}
    if not info["distinct"]:
        dupes = [k for k in layers if list(layers.values()).count(layers[k]) > 1]
        return {"passes": False,
                "reason": f"hook channels are identical ({', '.join(sorted(dupes))}) — "
                          "on-screen, spoken and visual must each do different work"}
    return {"passes": True, "reason": "hook channels are distinct"}


def describe(piece: dict) -> dict:
    """
    The full scroller decision record for one asset (ADR-002 Phase 1).
    Recorded on every asset so Phase 5 can eventually learn from it.
    """
    payoff = payoff_strength(piece)
    return {
        "scroller_mechanism": classify_mechanism(piece),
        "scroller_state":     classify_state(piece),
        "payoff_kinds":       payoff["kinds"],
        "payoff_score":       payoff["score"],
        "opens_loop":         payoff["opens_loop"],
        "hook_layers_distinct": hook_layers(piece)["distinct"],
        "basis": "classified from copy; selection is ADR-002 Phase 4",
    }
