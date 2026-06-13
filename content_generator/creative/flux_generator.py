"""
AI image generator — free provider cascade, no paid API required to start.

Provider priority:
  1. Hugging Face Inference API  — FREE with a free HF account token
                                   Model: FLUX.1-schnell (fastest FLUX variant)
                                   Signup: huggingface.co → Settings → Access Tokens
                                   Secret: HF_TOKEN (GitHub Actions)
                                   ~1,000 free images/month on free tier

  2. Pollinations AI             — Attempted as anonymous fallback.
                                   Free tier may work without a key in some regions.
                                   No signup needed (falls back silently if blocked).

  3. fal.ai Flux                 — Paid fallback, highest quality.
                                   Only used if FAL_KEY / FLUX_API_KEY secret is set.

  4. Pillow placeholder          — Always works, zero dependencies beyond Pillow.
                                   Generates a branded dark-background placeholder
                                   so the pipeline never hard-fails on images.

GitHub Actions setup (required for real images):
    Secrets → New secret → HF_TOKEN = your Hugging Face access token

Usage:
    from content_generator.creative.flux_generator import generate_image

    path = generate_image(
        "Purity Beans jar on dark marble, golden rim light, editorial photography",
        width=1080, height=1080,
        label="carousel_cover",
    )
    # Returns local file path always (placeholder if all AI providers fail)
"""
import datetime
import logging
import os
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
_OUT_DIR  = os.getenv("CREATIVE_OUTPUT_DIR", os.path.join("output", "creative"))
_TIMEOUT  = int(os.getenv("IMAGE_TIMEOUT", "90"))

# Provider keys
_HF_TOKEN = os.getenv("HF_TOKEN")                                    # free
_FAL_KEY  = os.getenv("FAL_KEY") or os.getenv("FLUX_API_KEY")        # paid fallback
if _FAL_KEY:
    os.environ.setdefault("FAL_KEY", _FAL_KEY)

# Hugging Face model — FLUX.1-schnell is fastest and free
_HF_MODEL = os.getenv(
    "HF_IMAGE_MODEL",
    "black-forest-labs/FLUX.1-schnell",
)
_FLUX_MODEL = os.getenv("FLUX_MODEL", "fal-ai/flux/dev")


# ── Public API ────────────────────────────────────────────────────────────────

def is_configured() -> bool:
    """
    Returns True if at least one image provider is available.
    Pillow placeholder always works so this is always True when Pillow is installed.
    """
    if _HF_TOKEN:
        return True
    try:
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        return False


def generate_image(
    prompt: str,
    width:  int = 1080,
    height: int = 1080,
    label:  str = "image",
    seed:   int = None,
) -> str | None:
    """
    Generate an image and save it locally.

    Tries providers in order: HuggingFace → Pollinations → fal.ai → Pillow placeholder.
    Always returns a path (placeholder at minimum) — never blocks the pipeline.

    Args:
        prompt: Image description. Brand guardrails applied automatically.
        width:  Output width in pixels (default 1080)
        height: Output height in pixels (default 1080)
        label:  Used in output filename for identification
        seed:   Optional fixed seed for reproducibility

    Returns:
        Local file path (never None if Pillow is installed).
    """
    from content_generator.creative.brand_guardrails import enforce_brand_prompt
    safe_prompt = enforce_brand_prompt(prompt)

    # 1. Hugging Face (free with token)
    if _HF_TOKEN:
        path = _huggingface(safe_prompt, width, height, label, seed)
        if path:
            return path

    # 2. Pollinations (free anonymous — works in some environments)
    path = _pollinations(safe_prompt, width, height, label, seed)
    if path:
        return path

    # 3. fal.ai (paid fallback)
    if _FAL_KEY:
        path = _fal_flux(safe_prompt, width, height, label, seed)
        if path:
            return path

    # 4. Pillow placeholder — guaranteed output
    return _pillow_placeholder(safe_prompt, width, height, label)


def generate_carousel_images(slides: list[dict], day: int) -> list[str]:
    """Generate one image per carousel slide."""
    paths = []
    for i, slide in enumerate(slides):
        prompt = slide.get("image_prompt") or slide.get("visual") or ""
        if not prompt:
            continue
        path = generate_image(
            prompt, width=1080, height=1080,
            label=f"carousel_slide_{i+1}_day{day}",
            seed=day * 100 + i,
        )
        if path:
            paths.append(path)
    return paths


def generate_reel_thumbnail(reel: dict, day: int, label: str = "reel") -> str | None:
    """Generate a 9:16 thumbnail for a reel."""
    prompt = (
        reel.get("visual_description")
        or reel.get("image_prompt")
        or reel.get("hook", "")
    )
    if not prompt:
        return None
    return generate_image(prompt, width=1080, height=1920, label=f"{label}_thumb_day{day}")


# ── Provider 1: Hugging Face Inference API (FREE) ─────────────────────────────

def _huggingface(
    prompt: str, width: int, height: int, label: str, seed: int | None
) -> str | None:
    """
    Call Hugging Face Inference API for FLUX.1-schnell.
    Free tier: ~1,000 images/month. Token from huggingface.co/settings/tokens.
    """
    import json

    url  = f"https://router.huggingface.co/hf-inference/models/{_HF_MODEL}"
    body = json.dumps({
        "inputs": prompt,
        "parameters": {
            "width":               min(width, 1024),    # HF free tier caps at 1024
            "height":              min(height, 1024),
            "num_inference_steps": 4,                   # schnell default
            **({"seed": seed} if seed is not None else {}),
        },
    }).encode("utf-8")

    logger.info("[image] HuggingFace %dx%d | model=%s | '%s...'",
                width, height, _HF_MODEL, prompt[:50])

    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {_HF_TOKEN}",
                "Content-Type":  "application/json",
                "User-Agent":    "PurityBeans/1.0",
            },
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=_TIMEOUT)

        if resp.status != 200:
            logger.warning("[image] HuggingFace HTTP %d", resp.status)
            return None

        image_bytes = resp.read()

        # HF returns JSON error or image bytes
        if image_bytes[:1] == b"{":
            error = image_bytes.decode("utf-8", errors="ignore")[:200]
            logger.warning("[image] HuggingFace returned JSON (model loading?): %s", error)
            return None

        if len(image_bytes) < 1000:
            logger.warning("[image] HuggingFace response too small (%d bytes)", len(image_bytes))
            return None

        logger.info("[image] HuggingFace OK (%d KB)", len(image_bytes) // 1024)
        return _save_image(image_bytes, label, ext="jpg")

    except Exception as e:
        logger.warning("[image] HuggingFace failed: %s", e)
        return None


# ── Provider 2: Pollinations AI (anonymous free) ──────────────────────────────

def _pollinations(
    prompt: str, width: int, height: int, label: str, seed: int | None
) -> str | None:
    """Anonymous Pollinations call — free in some regions, may return 402 elsewhere."""
    encoded = urllib.parse.quote(prompt, safe="")
    params  = {"width": width, "height": height}
    if seed is not None:
        params["seed"] = seed

    url = f"https://image.pollinations.ai/prompt/{encoded}?{urllib.parse.urlencode(params)}"
    logger.info("[image] Pollinations %dx%d | '%s...'", width, height, prompt[:50])

    try:
        req  = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        resp = urllib.request.urlopen(req, timeout=_TIMEOUT)

        if resp.status != 200:
            return None

        image_bytes = resp.read()

        # Pollinations returns JSON on error/limit exceeded even with HTTP 200
        if image_bytes[:1] == b"{":
            logger.debug("[image] Pollinations returned JSON (rate limited): %s", image_bytes[:200])
            return None

        if len(image_bytes) < 1000:
            return None

        logger.info("[image] Pollinations OK (%d KB)", len(image_bytes) // 1024)
        return _save_image(image_bytes, label, ext="jpg")

    except Exception as e:
        logger.debug("[image] Pollinations failed: %s", e)
        return None


# ── Provider 3: fal.ai Flux (paid fallback) ───────────────────────────────────

def _fal_flux(
    prompt: str, width: int, height: int, label: str, seed: int | None
) -> str | None:
    """fal.ai Flux — paid, used only if FAL_KEY is set and free providers failed."""
    try:
        import fal_client
    except ImportError:
        logger.debug("[image] fal-client not installed")
        return None

    try:
        logger.info("[image] fal.ai %dx%d | '%s...'", width, height, prompt[:50])
        args = {
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
            "num_images": 1,
            "output_format": "jpeg",
        }
        if seed is not None:
            args["seed"] = seed

        result     = fal_client.subscribe(_FLUX_MODEL, arguments=args, with_logs=False)
        image_url  = (result.get("images") or [{}])[0].get("url", "")
        if not image_url:
            return None

        req  = urllib.request.Request(image_url, headers={"User-Agent": "PurityBeans/1.0"})
        resp = urllib.request.urlopen(req, timeout=_TIMEOUT)
        logger.info("[image] fal.ai OK")
        return _save_image(resp.read(), label, ext="jpg")

    except Exception as e:
        logger.error("[image] fal.ai failed: %s", e)
        return None


# ── Provider 4: Pillow placeholder (guaranteed) ───────────────────────────────

def _pillow_placeholder(prompt: str, width: int, height: int, label: str) -> str | None:
    """
    Generate a branded dark placeholder image using Pillow.
    Zero external dependencies. Always succeeds if Pillow is installed.
    Brand spec: BG #0D0905, gold accent #C8962E, cream text #F5EED8.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.debug("[image] Pillow not installed — cannot generate placeholder")
        return None

    img  = Image.new("RGB", (width, height), color=(13, 9, 5))   # #0D0905 espresso
    draw = ImageDraw.Draw(img)

    # Gold accent bar at top
    bar_h = max(8, height // 60)
    draw.rectangle([(0, 0), (width, bar_h)], fill=(200, 150, 46))   # #C8962E

    # Brand name
    try:
        font_large = ImageFont.truetype("arial.ttf", size=max(28, width // 20))
        font_small = ImageFont.truetype("arial.ttf", size=max(16, width // 36))
    except Exception:
        font_large = ImageFont.load_default()
        font_small = font_large

    cx = width // 2
    draw.text((cx, height // 3),   "PURITY BEANS",    font=font_large, fill=(200, 150, 46), anchor="mm")
    draw.text((cx, height // 2),   "100% Pure Coffee", font=font_small, fill=(245, 238, 216), anchor="mm")

    # Truncated prompt
    short = (prompt[:60] + "...") if len(prompt) > 60 else prompt
    draw.text((cx, height * 2 // 3), short, font=font_small, fill=(120, 100, 80), anchor="mm")

    # Gold accent bar at bottom
    draw.rectangle([(0, height - bar_h), (width, height)], fill=(200, 150, 46))

    logger.info("[image] Pillow placeholder generated (%dx%d)", width, height)
    return _save_image(_pil_to_bytes(img), label, ext="jpg")


def _pil_to_bytes(img) -> bytes:
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


# ── Shared helper ─────────────────────────────────────────────────────────────

def _save_image(image_bytes: bytes, label: str, ext: str = "jpg") -> str | None:
    os.makedirs(_OUT_DIR, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    filepath = os.path.join(_OUT_DIR, f"{label}_{date_str}.{ext}")
    try:
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        logger.info("[image] Saved -> %s (%d KB)", filepath, len(image_bytes) // 1024)
        return filepath
    except Exception as e:
        logger.error("[image] Save failed: %s", e)
        return None
