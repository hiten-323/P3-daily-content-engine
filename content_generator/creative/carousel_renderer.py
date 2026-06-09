"""
Carousel renderer — produces branded PNG slide images from carousel text data.

Uses Pillow (PIL) if installed, otherwise returns metadata-only dicts.

Setup:
    pip install Pillow

Output: 1080x1080 PNG files, one per slide, saved to output/creative/

Brand spec:
  Background: #0D0905 (espresso black)
  Headline:   white, bold, large
  Body:       #F5EED8 (cream), regular weight
  Accent bar: #C8962E (gold) — 8px left border on headline slides
  Logo area:  bottom-right, "PURITY BEANS" text watermark in gold
"""
import logging
import os

logger = logging.getLogger(__name__)

_OUT_DIR = os.getenv("CREATIVE_OUTPUT_DIR", os.path.join("output", "creative"))

# Brand colours
_BG        = (13,  9,  5)      # espresso black
_GOLD      = (200, 150, 46)    # warm gold accent
_CREAM     = (245, 238, 216)   # cream white
_WHITE     = (255, 255, 255)
_SLIDE_W   = 1080
_SLIDE_H   = 1080
_PADDING   = 80


def is_configured() -> bool:
    try:
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        return False


def render_carousel(
    slides: list[dict],
    day: int,
    label: str = "carousel",
) -> list[str]:
    """
    Render carousel slides to PNG files.

    slides: list of dicts with keys: slide_number, headline, body_text (optional)
    day:    day_number (used in filename)
    label:  prefix for output filenames

    Returns list of file paths. Empty list if Pillow not installed.
    """
    if not is_configured():
        logger.info(
            "[carousel_renderer] Pillow not installed — skipping render. "
            "pip install Pillow"
        )
        return []

    os.makedirs(_OUT_DIR, exist_ok=True)
    paths = []
    for i, slide in enumerate(slides):
        path = _render_slide(slide, i + 1, day, label)
        if path:
            paths.append(path)
    logger.info("[carousel_renderer] Rendered %d/%d slides", len(paths), len(slides))
    return paths


def render_cover_slide(
    headline: str,
    subheadline: str = "",
    day: int         = 0,
) -> str | None:
    """Render the carousel cover (slide 0) with large headline."""
    slide = {"slide_number": 0, "headline": headline, "body_text": subheadline, "is_cover": True}
    return _render_slide(slide, 0, day, "carousel_cover")


def _render_slide(slide: dict, idx: int, day: int, label: str) -> str | None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    import datetime

    img  = Image.new("RGB", (_SLIDE_W, _SLIDE_H), color=_BG)
    draw = ImageDraw.Draw(img)

    # Gold accent bar on left
    draw.rectangle([(40, _PADDING), (48, _SLIDE_H - _PADDING)], fill=_GOLD)

    # Headline
    headline = slide.get("headline", slide.get("title", ""))
    body     = slide.get("body_text", slide.get("content", ""))
    slide_no = slide.get("slide_number", idx)

    # Slide number indicator (small, top-right)
    if slide_no and not slide.get("is_cover"):
        draw.text(
            (_SLIDE_W - _PADDING, _PADDING),
            f"{slide_no:02d}",
            fill=_GOLD,
            anchor="rt",
            font=_font(size=36),
        )

    # Headline text
    headline_y = _PADDING + 40
    _draw_wrapped_text(
        draw, headline,
        x=_PADDING + 30, y=headline_y,
        max_width=_SLIDE_W - _PADDING * 2 - 40,
        font=_font(size=72 if slide.get("is_cover") else 58),
        fill=_WHITE,
        line_spacing=1.2,
    )

    # Body text
    if body:
        body_y = headline_y + _estimate_text_height(headline, 58, _SLIDE_W - _PADDING * 2 - 40) + 60
        _draw_wrapped_text(
            draw, body,
            x=_PADDING + 30, y=body_y,
            max_width=_SLIDE_W - _PADDING * 2 - 40,
            font=_font(size=38),
            fill=_CREAM,
            line_spacing=1.4,
        )

    # Brand watermark bottom-right
    draw.text(
        (_SLIDE_W - _PADDING, _SLIDE_H - _PADDING),
        "PURITY BEANS",
        fill=_GOLD,
        anchor="rb",
        font=_font(size=28),
    )

    # Gold bottom accent line
    draw.rectangle([(_PADDING, _SLIDE_H - _PADDING + 20), (_SLIDE_W - _PADDING, _SLIDE_H - _PADDING + 26)], fill=_GOLD)

    # Save
    date_str = datetime.date.today().isoformat()
    filename = f"{label}_slide{idx:02d}_day{day}_{date_str}.png"
    filepath = os.path.join(_OUT_DIR, filename)
    img.save(filepath, "PNG", optimize=True)
    logger.debug("[carousel_renderer] Saved → %s", filepath)
    return filepath


def _font(size: int = 48):
    """Return best available font at given size."""
    try:
        from PIL import ImageFont
        # Try system fonts in order of preference
        for font_path in [
            "arial.ttf", "Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]:
            try:
                return ImageFont.truetype(font_path, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()
    except Exception:
        return None


def _draw_wrapped_text(draw, text, x, y, max_width, font, fill, line_spacing=1.3):
    """Draw text with word-wrapping."""
    if not text or font is None:
        return

    words    = text.split()
    lines    = []
    cur_line = ""

    for word in words:
        test = f"{cur_line} {word}".strip()
        try:
            bbox = draw.textbbox((0, 0), test, font=font)
            w    = bbox[2] - bbox[0]
        except Exception:
            w = len(test) * (font.size if hasattr(font, "size") else 20)

        if w <= max_width:
            cur_line = test
        else:
            if cur_line:
                lines.append(cur_line)
            cur_line = word

    if cur_line:
        lines.append(cur_line)

    line_h = (font.size if hasattr(font, "size") else 20) * line_spacing
    for i, line in enumerate(lines):
        draw.text((x, y + i * line_h), line, font=font, fill=fill)


def _estimate_text_height(text, font_size, max_width) -> int:
    """Rough height estimate for text block (chars-based, no PIL needed)."""
    chars_per_line = max(1, max_width // (font_size * 0.55))
    lines          = max(1, len(text) / chars_per_line)
    return int(lines * font_size * 1.4)
