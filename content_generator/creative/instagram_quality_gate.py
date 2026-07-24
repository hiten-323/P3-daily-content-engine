"""Hard QA for Instagram-native assets/copy before publish."""
from __future__ import annotations
import re

BAD_VISIBLE_LABELS = ("slide 1:", "slide 2:", "slide 3:", "headline:", "body_text:")
BAD_GLYPHS = ("\ufffd", "\u25a1")

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
    
    # Check for hook (either 'hook', 'hook_text', or 'chosen_hook')
    if not (plan.get("hook") or plan.get("hook_text") or plan.get("chosen_hook")):
        issues.append("missing first-second hook")
        
    # Check for motion/scene plan (either 'motion_plan', 'scenes', 'ai_video_motion_prompt', 'ai_video_prompts', 'frames', or 'script')
    if not (plan.get("motion_plan") or plan.get("scenes") or plan.get("ai_video_motion_prompt") or plan.get("ai_video_prompts") or plan.get("frames") or plan.get("script")):
        issues.append("missing motion/scene plan")
        
    # Check for audio plan (either 'audio_track', 'audio_recommendation', 'music_vibe', 'sound_suggestion', or 'audio'):
    if not (plan.get("audio_track") or plan.get("audio_recommendation") or plan.get("music_vibe") or plan.get("sound_suggestion") or plan.get("audio")):
        issues.append("missing audio plan")
        
    # Check for loopable ending (either 'loop_ending', 'loop_note', or 'loop_ending_note')
    if not (plan.get("loop_ending") or plan.get("loop_note") or plan.get("loop_ending_note")):
        issues.append("missing loopable ending")
        
    return {"ok":not issues,"issues":issues}

def publish_decision(copy_text="", surface="post", reel_plan=None) -> dict:
    checks=[inspect_copy(copy_text,surface)]
    if surface=="reel": checks.append(inspect_reel_plan(reel_plan or {}))
    issues=[i for c in checks for i in c["issues"]]
    return {"allow_publish":not issues,"issues":issues}
