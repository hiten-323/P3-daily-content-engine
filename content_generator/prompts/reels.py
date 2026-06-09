"""Reel prompt builder — one Instagram Reel script per call."""
from content_generator.prompts.brand import brand_block
from content_generator.rotation import WEBSITE_URL


def build(reel_id: str, arch: tuple, time_slot: str,
          hashtag_key: str, avoid: str) -> str:
    from config.brand_config import HASHTAG_SETS
    hs = HASHTAG_SETS[hashtag_key]

    return f"""{brand_block()}

Generate ONE Instagram Reel script for Purity Beans. Return a single JSON object.

{avoid}

REEL ID: {reel_id} | TIME SLOT: {time_slot}
HOOK ARCHETYPE: [{arch[0]}] — {arch[1]}
HASHTAGS (8-12 max): {hs}

Rules:
- frames.on_screen = visual text only. Never camera directions.
- frames.spoken = words said aloud only. Never repeat on_screen verbatim. Expand it.
- caption = paste-ready. Under 100 words including hashtags.

{{
  "id": "{reel_id}",
  "hook_archetype": "{arch[0]}",
  "hook_text": "4 WORDS MAX ALL CAPS",
  "hook_spoken": "First 3 spoken words — mid-action, never Hey guys",
  "frames": [
    {{"on_screen": "4 WORDS MAX ALL CAPS", "spoken": "8-12 words expanding the hook with a real Indian detail"}},
    {{"on_screen": "STAT OR FACT", "spoken": "The alarming number — Indian market context"}},
    {{"on_screen": "THE TWIST", "spoken": "The thing they did not expect"}},
    {{"on_screen": "THE VILLAIN", "spoken": "Name it precisely — chicory, additives, fake labels"}},
    {{"on_screen": "PURITY BEANS FIX", "spoken": "Rs18/cup. Zero chicory. Relief, not a pitch"}},
    {{"on_screen": "COMMENT PURE BELOW", "spoken": "CTA that feels rewarding to follow"}}
  ],
  "loop_note": "One sentence: how the last frame loops back to frame 1",
  "alt_hook": "A/B option — 4 words, different archetype",
  "caption": "Paste-ready caption with hook + value + {WEBSITE_URL} + hashtags. Under 100 words.",
  "visual_direction": "Shot type. Lighting. Motion. Colour grade. One paragraph.",
  "music_vibe": "Tempo, instrument, mood",
  "whatsapp_forward": "30-40 words. Indian voice. Sounds like a friend, not a brand."
}}"""
