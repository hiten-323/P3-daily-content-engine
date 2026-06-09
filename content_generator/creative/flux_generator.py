"""
Flux image generator — uses fal.ai Flux API for AI image generation.

Setup:
    pip install fal-client
    export FLUX_API_KEY="your_key_here"   # get from fal.ai

Model options (set FLUX_MODEL env var):
    flux/dev           — highest quality, slower  (default)
    flux/schnell       — fast, good quality
    flux-pro/v1.1      — best quality, premium tier

Usage:
    from content_generator.creative.flux_generator import generate_image
    path = generate_image(
        "Purity Beans jar on dark marble, golden rim light, editorial photography",
        width=1080, height=1080,
        label="carousel_cover"
    )
    # Returns: "output/creative/carousel_cover_20260609.png" or None if not configured
"""
import logging
import os

logger = logging.getLogger(__name__)

_MODEL    = os.getenv("FLUX_MODEL", "fal-ai/flux/dev")
_API_KEY  = os.getenv("FLUX_API_KEY")
_OUT_DIR  = os.getenv("CREATIVE_OUTPUT_DIR", os.path.join("output", "creative"))


def is_configured() -> bool:
    """Return True if Flux API is available and configured."""
    if not _API_KEY:
        return False
    try:
        import fal_client  # noqa: F401
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
    Generate an image using Flux API.

    Returns local file path on success, None if API not configured.

    Args:
        prompt: Image description. Brand guardrails applied automatically.
        width:  Output width in pixels (default 1080)
        height: Output height in pixels (default 1080)
        label:  Used in output filename for easy identification
        seed:   Optional fixed seed for reproducibility
    """
    from content_generator.creative.brand_guardrails import enforce_brand_prompt
    safe_prompt = enforce_brand_prompt(prompt)

    if not _API_KEY:
        logger.info("[flux] FLUX_API_KEY not set — returning None (prompt: %s...)", safe_prompt[:60])
        return None

    try:
        import fal_client
    except ImportError:
        logger.debug("[flux] fal-client not installed — pip install fal-client")
        return None

    try:
        os.environ.setdefault("FAL_KEY", _API_KEY)
        logger.info("[flux] Generating %dx%d image: '%s...'", width, height, safe_prompt[:50])

        arguments = {
            "prompt":      safe_prompt,
            "image_size":  {"width": width, "height": height},
            "num_images":  1,
            "output_format": "jpeg",
        }
        if seed is not None:
            arguments["seed"] = seed

        result = fal_client.subscribe(
            _MODEL,
            arguments=arguments,
            with_logs=False,
        )

        images = result.get("images", [])
        if not images:
            logger.warning("[flux] No images in response")
            return None

        image_url = images[0].get("url", "")
        if not image_url:
            return None

        return _download_image(image_url, label)

    except Exception as e:
        logger.error("[flux] Generation failed: %s", e)
        return None


def generate_carousel_images(slides: list[dict], day: int) -> list[str]:
    """
    Generate one image per carousel slide.
    Returns list of local file paths (may be shorter than slides if some fail).
    """
    paths = []
    for i, slide in enumerate(slides):
        prompt = slide.get("image_prompt") or slide.get("visual") or ""
        if not prompt:
            continue
        path = generate_image(
            prompt,
            width=1080, height=1080,
            label=f"carousel_slide_{i+1}_day{day}",
            seed=day * 100 + i,  # deterministic seed per slide per day
        )
        if path:
            paths.append(path)
    return paths


def _download_image(url: str, label: str) -> str | None:
    """Download image from URL to local file. Returns path or None."""
    import datetime
    import urllib.request

    os.makedirs(_OUT_DIR, exist_ok=True)
    date_str  = datetime.date.today().isoformat()
    filename  = f"{label}_{date_str}.jpg"
    filepath  = os.path.join(_OUT_DIR, filename)

    try:
        urllib.request.urlretrieve(url, filepath)
        logger.info("[flux] Saved → %s", filepath)
        return filepath
    except Exception as e:
        logger.error("[flux] Download failed: %s", e)
        return None
