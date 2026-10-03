"""Hard QA for Instagram-native assets/copy before publish."""
from __future__ import annotations
import re

BAD_VISIBLE_LABELS = ("slide 1:", "slide 2:", "slide 3:", "headline:", "body_text:")
BAD_GLYPHS = ("\ufffd", "\u25a1")

# Prompt, schema and quality-gate names for the same idea. A growth reel
# writes `chosen_hook` / `script` / `sound_suggestion`; a brand reel writes
# `hook_text` / `frames` / `music_vibe`. Any one of these is enough.
HOOK_KEYS = ("hook", "hook_text", "chosen_hook", "hook_line")
MOTION_KEYS = (
    "motion_plan", "scenes", "ai_video_motion_prompt", "ai_video_prompts",
    "frames", "script",
)
AUDIO_PLAN_KEYS = (
    "audio_track", "audio_recommendation", "music_vibe", "sound_suggestion",
    "audio", "audio_plan", "audio_direction",
)
LOOP_KEYS = ("loop_ending", "loop_note", "loop_ending_note", "loopable_ending")


def _has_any(plan: dict, keys: tuple) -> bool:
    for key in keys:
        value = plan.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and len(value) == 0:
            continue
        return True
    return False

def inspect_copy(text: str, surface: str="post") -> dict:
    text=(text or "").strip()
    issues=[]
    low=text.lower()
    if any(x in low for x in BAD_VISIBLE_LABELS): issues.append("internal slide/template label leaked into visible copy")
    if any(x in text for x in BAD_GLYPHS): issues.append("unsupported/replacement glyph detected")
    if surface in ("carousel","story") and len(text)>220: issues.append("too much on-canvas text")
    if surface=="reel" and len(text)>140: issues.append("reel overlay/copy too dense")
    words=re.findall(r"\b[\w'-]+\b",text)
    if surface in ("carousel","story") and len(words)>34: issues.append("word count too high for mobile creative")
    return {"ok":not issues,"issues":issues}

def inspect_reel_plan(plan: dict) -> dict:
    issues=[]
    duration=float(plan.get("duration_seconds") or 0)
    if duration and duration>35: issues.append("reel too long for discovery-first default")
    
    if not _has_any(plan, HOOK_KEYS):
        issues.append("missing first-second hook")
    if not _has_any(plan, MOTION_KEYS):
        issues.append("missing motion/scene plan")
    if not _has_any(plan, AUDIO_PLAN_KEYS):
        issues.append("missing audio plan")
    if not _has_any(plan, LOOP_KEYS):
        issues.append("missing loopable ending")
        
    return {"ok":not issues,"issues":issues}

def publish_decision(copy_text="", surface="post", reel_plan=None) -> dict:
    checks=[inspect_copy(copy_text,surface)]
    if surface=="reel": checks.append(inspect_reel_plan(reel_plan or {}))
    issues=[i for c in checks for i in c["issues"]]
    return {"allow_publish":not issues,"issues":issues}
