"""
Thumbnail generator — creates Reel / YouTube Short cover images.

Two modes:
  1. Flux AI (FLUX_API_KEY set) — photorealistic product shot
  2. Pillow render (Pillow installed) — text + brand treatment thumbnail
  3. Metadata only — returns prompt + spec for manual creation

Output: 1080x1920 (9:16 vertical) for Reels, 1280x720 (16:9) for YouTube.
"""
import logging
import os

logger = logging.getLogger(__name__)

_OUT_DIR = os.getenv("CREATIVE_OUTPUT_DIR", os.path.join("output", "creative"))


def generate_reel_thumbnail(
    reel_data: dict,
    day: int,
    label: str = "reel",
) -> dict:
    """
    Generate or describe a Reel thumbnail.

    Returns:
    {
        "file_path":  "output/creative/reel_1_thumb_day42.jpg" or None,
        "mode":       "flux" | "pillow" | "prompt_only",
        "prompt":     "<image generation prompt>",
        "spec":       "1080x1920, 9:16 vertical",
        "hook_text":  "<hook for text overlay>",
    }
    """
    hook   = reel_data.get("hook_text", "")
    visual = reel_data.get("visual_direction", "")
    reel_id = reel_data.get("id", label)

    prompt = _build_thumbnail_prompt(hook, visual, "reel")

    # Try Flux first
    try:
        from content_generator.creative.flux_generator import generate_image, is_configured
        if is_configured():
            path = generate_image(
                prompt, width=1080, height=1920,
                label=f"{reel_id}_thumb_day{day}",
                seed=day,
            )
            if path:
                return {"file_path": path, "mode": "flux", "prompt": prompt,
                        "spec": "1080x1920", "hook_text": hook}
    except Exception as e:
        logger.debug("[thumbnail] Flux failed: %s", e)

    # Try Pillow render
    try:
        from content_generator.creative.carousel_renderer import is_configured as pillow_ok
        if pillow_ok():
            path = _render_pillow_thumbnail(hook, visual, day, label=f"{reel_id}_thumb")
            if path:
                return {"file_path": path, "mode": "pillow", "prompt": prompt,
                        "spec": "1080x1920", "hook_text": hook}
    except Exception as e:
        logger.debug("[thumbnail] Pillow render failed: %s", e)

    # Fallback — return prompt for manual creation
    return {
        "file_path": None,
        "mode":      "prompt_only",
        "prompt":    prompt,
        "spec":      "1080x1920 vertical, 9:16 aspect ratio",
        "hook_text": hook,
    }


def generate_yt_thumbnail(
    yt_data: dict,
    day: int,
) -> dict:
    """Generate or describe a YouTube Short thumbnail (1280x720)."""
    product = yt_data.get("product", "Purity Beans")
    prompt  = (
        f"YouTube thumbnail — {product} coffee jar, bold cinematic composition, "
        f"dark background, large readable headline space, warm gold accent light, "
        f"16:9 horizontal framing, premium FMCG editorial style"
    )
    try:
        from content_generator.creative.flux_generator import generate_image, is_configured
        if is_configured():
            path = generate_image(prompt, width=1280, height=720, label=f"yt_thumb_day{day}")
            if path:
                return {"file_path": path, "mode": "flux", "prompt": prompt, "spec": "1280x720"}
    except Exception:
        pass

    return {"file_path": None, "mode": "prompt_only", "prompt": prompt, "spec": "1280x720"}


def _build_thumbnail_prompt(hook: str, visual: str, content_type: str) -> str:
    from content_generator.creative.brand_guardrails import enforce_brand_prompt
    base = (
        f"Instagram Reel thumbnail — Purity Beans coffee product hero shot, "
        f"vertical 9:16 framing, bold text space in upper third for hook overlay, "
        f"dark cinematic background, warm amber light beam, premium FMCG aesthetic"
    )
    if visual:
        base = f"{visual}. {base}"
    return enforce_brand_prompt(base)


def _render_pillow_thumbnail(
    hook_text: str,
    visual_note: str,
    day: int,
    label: str = "thumb",
) -> str | None:
    """Render a simple branded thumbnail with text overlay using Pillow."""
    try:
        from PIL import Image, ImageDraw
        from content_generator.creative.carousel_renderer import _font, _draw_wrapped_text, _BG, _GOLD, _WHITE, _CREAM
    except ImportError:
        return None

    import datetime
    os.makedirs(_OUT_DIR, exist_ok=True)

    img  = Image.new("RGB", (1080, 1920), color=_BG)
    draw = ImageDraw.Draw(img)

    # Gradient-like top-to-bottom darkening via rectangle overlays
    for i in range(20):
        alpha = int(i * 6)
        draw.rectangle([(0, 1920 - i * 60), (1080, 1920)],
                       fill=(max(0, 13 - i), max(0, 9 - i), max(0, 5 - i)))

    # Gold diagonal accent
    draw.polygon([(0, 600), (200, 0), (220, 0), (20, 600)], fill=_GOLD)

    # Hook text
    if hook_text:
        _draw_wrapped_text(
            draw, hook_text,
            x=80, y=200,
            max_width=920,
            font=_font(size=80),
            fill=_WHITE,
            line_spacing=1.3,
        )

    # Brand mark
    draw.text((1080 - 60, 1920 - 80), "PURITY BEANS", fill=_GOLD,
              anchor="rb", font=_font(size=40))

    date_str = datetime.date.today().isoformat()
    filepath = os.path.join(_OUT_DIR, f"{label}_day{day}_{date_str}.png")
    img.save(filepath, "PNG")
    return filepath
