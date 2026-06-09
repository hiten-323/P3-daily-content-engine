"""YouTube Shorts 5-scene script prompt."""
from content_generator.prompts.brand import brand_block
from content_generator.rotation import COMMERCIAL_EMOTIONS


def build(product: str, day: int) -> str:
    emotion = COMMERCIAL_EMOTIONS[day % len(COMMERCIAL_EMOTIONS)]

    return f"""{brand_block()}

Generate ONE YouTube Shorts script for Purity Beans. Return a single JSON object.

PRODUCT: {product}
EMOTION ARC: {emotion[0]} — {emotion[1]}

Rules:
- scenes.on_screen = text displayed on screen only. Max 4 words per scene.
- scenes.spoken = voiceover words only. No production notes.
- Total duration = 27 seconds across 5 scenes.

{{
  "product": "{product}",
  "tagline": "Fresh ad tagline — max 6 words — not the brand tagline",
  "emotion_arc": "{emotion[0]}",
  "scenes": [
    {{"scene": 1, "type": "problem",        "duration_s": 5, "on_screen": "4 WORDS MAX — precise painful Indian moment",       "spoken": "8-12 words — raw first-person pain, no product",          "visual_direction": "Shot, lighting, one specific scene"}},
    {{"scene": 2, "type": "agitation",      "duration_s": 5, "on_screen": "4 WORDS MAX — the betrayal visible",               "spoken": "8-12 words — the reveal that makes them angry",          "visual_direction": "Label close-up or chicory granule reveal"}},
    {{"scene": 3, "type": "product_reveal", "duration_s": 7, "on_screen": "4 WORDS MAX — product name + one pure truth",      "spoken": "8-12 words — relief, quiet confidence, not hype",        "visual_direction": "Slow product reveal, gold light, steam"}},
    {{"scene": 4, "type": "benefit",        "duration_s": 5, "on_screen": "4 WORDS MAX — specific result this product gives", "spoken": "8-12 words — transformation tied to this product",       "visual_direction": "Person + mug, natural light, real energy"}},
    {{"scene": 5, "type": "cta",            "duration_s": 5, "on_screen": "4 WORDS MAX — low friction entry",                 "spoken": "6-10 words — gentle urgency, never pushy",              "visual_direction": "Static product, logo, URL held 2 seconds"}}
  ],
  "audio_direction": "Music bed genre + tempo + voiceover tone (Indian accent, gender, age). Sound design cues: when silence lands, when bass hits.",
  "edit_pacing": "Cut timing per scene — e.g. 1.5s cuts scenes 1-2, 3s hold on scene 3 reveal"
}}"""
