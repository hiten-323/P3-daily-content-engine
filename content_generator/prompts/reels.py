"""Reel prompt builder — full publish-ready Instagram Reel asset."""
from content_generator.prompts.brand import brand_block
from content_generator.rotation import WEBSITE_URL, get_todays_viral_idea, get_todays_hook

HASHTAG_25 = (
    "#Coffee #CoffeeLover #InstantCoffee #MorningCoffee #CoffeeTime "
    "#PremiumCoffee #FreezeDriedCoffee #GourmetCoffee #PureCoffee #CoffeeCommunity "
    "#IndianCoffee #CoffeeIndia #MadeInIndia #IndianBrands #SupportIndianBrands "
    "#CoffeeAddict #CoffeeDaily #CoffeeGram #CoffeeCulture #CoffeeLife "
    "#PurityBeans #PurityBeansCoffee #PurityBeansExperience #BrewPure #PureCoffeeExperience"
)


def build(reel_id: str, arch: tuple, time_slot: str,
          hashtag_key: str, avoid: str, day: int = 0) -> str:
    viral_idea = get_todays_viral_idea(day)
    suggested_hook = get_todays_hook(day)

    return f"""{brand_block()}

Generate ONE complete publish-ready Instagram Reel for Purity Beans. Return a single JSON object.

{avoid}

REEL ID: {reel_id} | TIME SLOT: {time_slot}
HOOK ARCHETYPE: [{arch[0]}] — {arch[1]}
TODAY'S VIRAL CONTENT ANGLE: {viral_idea}
SUGGESTED OPENING HOOK: "{suggested_hook}" (adapt or improve — do not copy verbatim)

SUBJECT TEST (mandatory before writing):
Ask: Is this something urban Indian coffee drinkers are curious about but nobody is explaining simply?
If yes → proceed. If no → reframe the angle until it passes.
The best hooks cannot save a topic nobody cares about.

ABSOLUTE RULES:
- NEVER invent statistics or percentages
- NEVER make medical claims
- NEVER use generic AI language
- Caption MUST be 150-250 words
- Brand name 'Purity Beans' MUST appear in caption
- Website '{WEBSITE_URL}' MUST appear in caption and CTA
- comment_trigger, save_trigger, share_trigger, ai_image_hook_prompt, ai_video_motion_prompt are MANDATORY fields

{{
  "id": "{reel_id}",
  "hook_archetype": "{arch[0]}",
  "hook_text": "4 WORDS MAX ALL CAPS — stops the scroll instantly",
  "hook_spoken": "First 3 spoken words — mid-action, never Hey guys",
  "frames": [
    {{"on_screen": "4 WORDS MAX ALL CAPS", "spoken": "8-12 words expanding the hook with a real Indian detail"}},
    {{"on_screen": "THE PROBLEM", "spoken": "What most Indians drink without knowing — specific, not statistical"}},
    {{"on_screen": "THE TWIST", "spoken": "The thing they did not expect — contrarian, relatable"}},
    {{"on_screen": "THE VILLAIN", "spoken": "Name it precisely — chicory, preservatives, artificial aroma"}},
    {{"on_screen": "PURITY BEANS FIX", "spoken": "Zero preservatives. No artificial aroma. 100% coffee. Relief, not a pitch."}},
    {{"on_screen": "COMMENT PURE BELOW", "spoken": "CTA that feels rewarding to follow"}}
  ],
  "loop_note": "One sentence: how the last frame connects back to frame 1 for infinite loop",
  "alt_hook": "A/B option — 4 words, completely different archetype",
  "caption": "HOOK LINE (stops scroll, max 12 words).\\n\\nShort story or insight that coffee lovers relate to. Introduce Purity Beans naturally — not as an ad. Explain why real coffee drinkers should care. Mention: No preservatives. No artificial aroma. 100% coffee. Available at {WEBSITE_URL}\\n\\nThis is a 150-250 word paste-ready caption with emotional storytelling, brand facts woven in naturally, and a clear reason to act.\\n\\nShop now: {WEBSITE_URL}",
  "cta": "Direct action line — shop / visit / comment. Must include {WEBSITE_URL}",
  "comment_trigger": "Comment COFFEE below if you refuse to drink chicory disguised as coffee.",
  "save_trigger": "Save this before your next grocery run so you never buy the wrong coffee again.",
  "share_trigger": "Share with someone who starts every morning with coffee — they deserve to know.",
  "seo_keywords": ["premium instant coffee", "gourmet instant coffee", "freeze dried coffee", "agglomerated coffee", "best instant coffee india", "coffee without preservatives", "pure instant coffee", "coffee lovers india", "instant coffee brand india"],
  "hashtags": "{HASHTAG_25}",
  "visual_direction": "Shot type. Lighting. Motion. Colour grade. Dark marble surfaces, warm amber light, Purity Beans jar prominent.",
  "music_vibe": "Tempo, instrument, mood — matches the emotional arc",
  "whatsapp_forward": "30-40 words. Indian voice. Sounds like a friend forwarding, not a brand broadcasting.",
  "ai_image_hook_prompt": "A detailed, paste-ready image generation prompt for Nano Banana Pro or GPT Image 2. MUST include: vertical 9:16 format, photographic (never 'render'), 85mm f/1.8, shallow depth of field, dark cinematic background, warm amber/gold accent light on Purity Beans jar, a human in frame (human anchor). REALISM INGREDIENTS required in the prompt text: visible skin pores, flyaway hairs, fabric wrinkles, one light source with correct shadow direction, contact shadow under the jar, environment reflections on glass, one lived-in detail (droplet, smudge, scattered granules), subject slightly off-center, natural grain. BANNED words: perfect, flawless, stunning, 3D, render, CGI, illustration. This is the STILL FRAME the reel opens on. 80-120 words.",
  "ai_video_motion_prompt": "A paste-ready motion prompt for Seedance 2.0 or Veo. Describes ONLY the motion added to the still frame. Rules: the person stays calm but BREATHES (chest movement, micro blinks). The Purity Beans jar stays steady. Background elements move with real physics (steam disperses, liquid has weight, particles fall not float). Camera: slow steady push-in or locked-off, 24fps film feel. Faces stay stable — no morphing. 40-60 words."
}}"""
