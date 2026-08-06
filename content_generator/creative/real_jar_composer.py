"""
Real Jar Composer — brand images built FROM actual jar photos, not AI guesses.

Why this exists:
  FLUX / Pollinations are text-to-image APIs. They cannot see reference
  images — listing file paths in the prompt does nothing. Result: invented
  jars with gibberish labels posted to Instagram.

This module guarantees the real product:
  - Base: an actual photo from brand_assets/puritybeans_*.png
    (product-aware, rotates through products/sizes/angles by day+slide
    so no two posts look the same)
  - Canvas: brand palette (#0D0905 espresso, #C8962E gold, #F5EED8 cream)
  - Overlay: slide headline + body + Purity Beans / p3online.in footer
  - Pillow only — works on any runner, zero API calls, zero hallucination.
"""
from __future__ import annotations
import logging
import os

logger = logging.getLogger(__name__)

_OUT_DIR = os.getenv("CREATIVE_OUTPUT_DIR", os.path.join("output", "creative"))
_ASSETS  = "brand_assets"

_BG     = (13, 9, 5)        # #0D0905 espresso black
_GOLD   = (200, 150, 46)    # #C8962E
_CREAM  = (245, 238, 216)   # #F5EED8
_MUTED  = (170, 150, 120)

_PRODUCTS = ["ultra_blend", "bold", "purista", "purica"]
_SIZES    = ["100g", "50g"]
_ANGLES   = ["front", "lifestyle", "side", "variant"]


def _all_jar_photos() -> list[str]:
    paths = []
    for p in _PRODUCTS:
        for s in _SIZES:
            for a in _ANGLES:
                fp = os.path.join(_ASSETS, f"puritybeans_{p}_{s}_{a}.png")
                if os.path.exists(fp):
                    paths.append(fp)
    return paths


def pick_jar_photo(day: int, idx: int = 0, product: str | None = None) -> str | None:
    """Deterministically rotate through real jar photos so posts differ daily."""
    if product:
        pool = [p for p in _all_jar_photos() if f"_{product}_" in p]
        pool = pool or _all_jar_photos()
    else:
        pool = _all_jar_photos()
    if not pool:
        logger.warning("[real_jar] No jar photos found in %s", _ASSETS)
        return None
    return pool[(day * 3 + idx) % len(pool)]


def _font(role: str, size: int):
    from PIL import ImageFont
    if role == "title":
        # Georgia (elegant serif) -> fallbacks
        candidates = ["georgiab.ttf", "georgia.ttf", "timesbd.ttf", "times.ttf", "arialbd.ttf"]
    elif role == "body":
        # Segoe UI (clean, high legibility sans-serif) -> fallbacks
        candidates = ["segoeui.ttf", "calibri.ttf", "arial.ttf"]
    elif role == "footer":
        # Segoe UI Bold -> fallbacks
        candidates = ["segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"]
    else:
        candidates = ["segoeui.ttf", "arial.ttf"]

    extended_candidates = []
    for c in candidates:
        extended_candidates.append(c)
        if os.name == "nt":
            extended_candidates.append(os.path.join("C:\\Windows\\Fonts", c))
        else:
            extended_candidates.extend([
                os.path.join("/usr/share/fonts/truetype/msttcorefonts", c),
                os.path.join("/usr/share/fonts/truetype/dejavu", c),
                os.path.join("/usr/share/fonts/truetype/freefont", c)
            ])

    for c in extended_candidates:
        try:
            return ImageFont.truetype(c, size=size)
        except Exception:
            continue
    try:
        from PIL import ImageFont as IF
        return IF.load_default(size=size)
    except Exception:
        from PIL import ImageFont as IF
        return IF.load_default()


_SCAFFOLD = __import__("re").compile(
    r"^\s*(slide|frame|scene|step|part|hook|headline|title)\s*(no\.?\s*)?\d*\s*[:\-–—.)]\s*",
    __import__("re").I)


def _sanitize_text(text: str) -> str:
    """Last line of defence before pixels: no 'Slide 1:' labels, no tofu glyphs."""
    t = str(text or "").strip()
    for _ in range(3):
        new = _SCAFFOLD.sub("", t).strip()
        if new == t:
            break
        t = new
    for bad, good in (("•", "|"), ("·", "|"), ("–", "-"),
                      ("—", "-"), ("’", "'"), ("“", '"'), ("”", '"')):
        t = t.replace(bad, good)
    return t


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    text = _sanitize_text(text)
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:4]


def compose_post_image(
    headline: str,
    body: str = "",
    day: int = 0,
    idx: int = 0,
    width: int = 1080,
    height: int = 1080,
    product: str | None = None,
    label: str = "brand_post",
) -> str | None:
    """
    Build one branded image: real jar photo + headline + body + footer.
    Returns saved file path, or None if Pillow/photos unavailable.
    """
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        logger.warning("[real_jar] Pillow not installed")
        return None

    jar_path = pick_jar_photo(day, idx, product)
    if not jar_path:
        return None

    is_lifestyle = "lifestyle" in os.path.basename(jar_path).lower()

    canvas = Image.new("RGB", (width, height), _BG)

    # 1. Process and draw/paste the main background or jar photo
    try:
        jar = Image.open(jar_path).convert("RGB")
        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resample_filter = Image.LANCZOS

        if is_lifestyle:
            # Lifestyle photo: scale to COVER the entire canvas, crop center, and apply dark overlay
            img_ratio = jar.width / jar.height
            canvas_ratio = width / height
            if img_ratio > canvas_ratio:
                new_h = height
                new_w = int(height * img_ratio)
            else:
                new_w = width
                new_h = int(width / img_ratio)
            
            jar = jar.resize((new_w, new_h), resample_filter)
            x_offset = (new_w - width) // 2
            y_offset = (new_h - height) // 2
            jar = jar.crop((x_offset, y_offset, x_offset + width, y_offset + height))
            canvas.paste(jar, (0, 0))
            
            # Apply dark espresso overlay to ensure high copy contrast
            overlay = Image.new("RGBA", (width, height), (13, 9, 5, 130)) # ~50% opacity
            canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
        else:
            # Regular jar photo: draw radial spotlight and paste jar centered at bottom
            try:
                glow_size = int(width * 0.6)
                glow_mask = Image.new("L", (glow_size, glow_size), 0)
                glow_draw = ImageDraw.Draw(glow_mask)
                for r in range(glow_size // 2, 0, -2):
                    alpha = int(210 * (1.0 - (r / (glow_size // 2))) ** 2)
                    glow_draw.ellipse(
                        [(glow_size // 2 - r, glow_size // 2 - r), 
                         (glow_size // 2 + r, glow_size // 2 + r)], 
                        fill=alpha
                    )
                glow_mask = glow_mask.filter(ImageFilter.GaussianBlur(20))
                gold_glow = Image.new("RGB", (glow_size, glow_size), (40, 28, 12)) 
                gx = (width - glow_size) // 2
                gy = height - max(8, height // 90) - int(height * 0.55)
                canvas.paste(gold_glow, (gx, gy), mask=glow_mask)
            except Exception as e:
                logger.debug("[real_jar] Radial spotlight failed: %s", e)

            # Paste jar at bottom 55%
            target_h = int(height * 0.52)
            ratio    = target_h / jar.height
            jar      = jar.resize((int(jar.width * ratio), target_h), resample_filter)
            if jar.width > width - 80:
                r   = (width - 80) / jar.width
                jar = jar.resize((width - 80, int(jar.height * r)), resample_filter)
            jx = (width - jar.width) // 2
            jy = height - max(8, height // 90) - jar.height - int(height * 0.02)
            canvas.paste(jar, (jx, jy))
            
    except Exception as e:
        logger.warning("[real_jar] Could not process jar photo %s: %s", jar_path, e)
        return None

    draw = ImageDraw.Draw(canvas)
    bar = max(8, height // 90)
    draw.rectangle([(0, 0), (width, bar)], fill=_GOLD)
    draw.rectangle([(0, height - bar), (width, height)], fill=_GOLD)

    # Headline (top area)
    margin = int(width * 0.07)
    max_w  = width - 2 * margin
    h_font = _font("title", max(34, width // 14))
    y      = int(height * 0.06)
    for line in _wrap(draw, headline.upper(), h_font, max_w):
        draw.text((width // 2, y), line, font=h_font, fill=_CREAM, anchor="ma")
        y += int(h_font.size * 1.18)

    # Body
    if body:
        b_font = _font("body", max(20, width // 32))
        y += int(height * 0.015)
        for line in _wrap(draw, body, b_font, max_w):
            draw.text((width // 2, y), line, font=b_font, fill=_MUTED, anchor="ma")
            y += int(b_font.size * 1.3)

    # Footer brand strip (above bottom gold bar, over dark strip)
    f_font = _font("footer", max(18, width // 36))
    strip_h = int(height * 0.045)
    
    # Gold separator line above the footer strip
    draw.line([(0, height - bar - strip_h), (width, height - bar - strip_h)], fill=_GOLD, width=2)
    
    draw.rectangle([(0, height - bar - strip_h), (width, height - bar)], fill=(20, 14, 8))
    draw.text((width // 2, height - bar - strip_h // 2),
              "PURITY BEANS  |  100% COFFEE, ZERO CHICORY  |  p3online.in",
              font=f_font, fill=_GOLD, anchor="mm")

    # Save
    import datetime, io
    os.makedirs(_OUT_DIR, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    path = os.path.join(_OUT_DIR, f"{label}_{date_str}.jpg")
    canvas.save(path, "JPEG", quality=88)
    logger.info("[real_jar] Composed %s from real photo %s", path, os.path.basename(jar_path))
    return path


def compose_carousel_slides(slides: list[dict], day: int) -> list[str]:
    """One branded 1080x1080 image per slide — each with a DIFFERENT real jar photo."""
    paths = []
    for i, slide in enumerate(slides):
        if isinstance(slide, str):
            heading, body = slide, ""
        else:
            heading = str(slide.get("heading") or slide.get("title") or "")
            body    = str(slide.get("body") or "")[:160]
        if not heading:
            continue
        p = compose_post_image(
            headline=heading, body=body, day=day, idx=i,
            width=1080, height=1080, label=f"carousel_slide_{i+1}_day{day}",
        )
        if p:
            paths.append(p)
    return paths


def compose_reel_thumbnail(reel: dict, day: int, label: str = "reel_1") -> str | None:
    """9:16 thumbnail from the reel's hook text + a real jar photo."""
    headline = str(reel.get("hook_text") or reel.get("hook") or "REAL COFFEE. ZERO CHICORY.")
    return compose_post_image(
        headline=headline, body="", day=day, idx=7,
        width=1080, height=1920, label=f"{label}_thumb_day{day}",
    )
