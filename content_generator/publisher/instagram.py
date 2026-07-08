"""
Instagram auto-publisher — posts carousels and single images via Meta Graph API.

Prerequisites (one-time setup):
  1. Instagram Business or Creator account
  2. Facebook Page connected to that Instagram account
  3. Meta App with instagram_basic + instagram_content_publish permissions
  4. A long-lived Page Access Token (valid 60 days, renewable)

Required secrets:
    INSTAGRAM_ACCOUNT_ID     — Your Instagram Business Account ID
                               Find: Graph API Explorer → /me/accounts → instagram_business_account
    INSTAGRAM_ACCESS_TOKEN   — Long-lived Page Access Token with publishing permissions
                               Generate: developers.facebook.com → Tools → Access Token Debugger

What gets posted:
    - Carousel (multi-image): all generated carousel slide images
    - Single image: if only one image available (carousel cover)
    - Caption: from carousel.caption or reel hook

Note on Reels:
    Instagram Reels require an actual video file. Since the engine generates
    scripts (not rendered video), Reels auto-posting is skipped here.
    Add RUNWAY_API_KEY to enable video generation → Reels posting.

API flow for carousel:
    1. POST /{ig-user-id}/media for each image → get container_id
    2. POST /{ig-user-id}/media with carousel children → get carousel_container_id
    3. POST /{ig-user-id}/media_publish with carousel_container_id → published!
"""
from __future__ import annotations
import logging
import os
import time

logger = logging.getLogger(__name__)

_GRAPH_API = "https://graph.facebook.com/v18.0"


def is_configured() -> bool:
    return bool(os.getenv("INSTAGRAM_ACCOUNT_ID")) and bool(os.getenv("INSTAGRAM_ACCESS_TOKEN"))


def post_content(content: dict, day: int = 0) -> dict:
    """
    Post today's content to Instagram.

    Tries carousel first (if multiple images). Falls back to single image post.

    Returns:
        {"success": bool, "media_id": str, "permalink": str, "error": str|None}
    """
    if not is_configured():
        logger.info("[instagram] Not configured — INSTAGRAM_ACCOUNT_ID or INSTAGRAM_ACCESS_TOKEN missing")
        return {"success": False, "media_id": "", "permalink": "", "error": "not_configured"}

    images  = _find_carousel_images(content)
    caption = _extract_caption(content, day=day)

    if not images:
        logger.warning("[instagram] No images found — skipping Instagram post")
        return {"success": False, "media_id": "", "permalink": "", "error": "no_images"}

    if len(images) >= 2:
        result = _post_carousel(images[:10], caption)   # Instagram max 10
    else:
        result = _post_single_image(images[0], caption)

    # Expose the exact tags posted so insights can attribute performance to them
    result["hashtags_used"] = " ".join(w for w in caption.split() if w.startswith("#"))

    if result["success"]:
        logger.info("[instagram] Day %d posted | id=%s", day, result["media_id"])
    else:
        logger.error("[instagram] Day %d failed: %s", day, result["error"])

    return result


# 25-tag fallback: 5 broad + 5 niche + 5 Indian + 5 discovery + 5 brand
_FALLBACK_HASHTAGS = (
    "#Coffee #CoffeeLover #InstantCoffee #MorningCoffee #CoffeeTime "
    "#PremiumCoffee #FreezeDriedCoffee #GourmetCoffee #PureCoffee #CoffeeCommunity "
    "#IndianCoffee #CoffeeIndia #MadeInIndia #IndianBrands #SupportIndianBrands "
    "#CoffeeAddict #CoffeeDaily #CoffeeGram #CoffeeCulture #CoffeeLife "
    "#PurityBeans #PurityBeansCoffee #NoChicory #BrewPure #PureCoffeeExperience"
)


def _extract_caption(content: dict, day: int = 0) -> str:
    """
    Build the full viral-ready Instagram caption:
    caption body + comment trigger + save trigger + adaptive 25 hashtags.
    """
    # Try carousel first, then first reel
    piece = None
    carousel = content.get("carousel") or {}
    if isinstance(carousel, dict) and (carousel.get("caption") or carousel.get("hook")):
        piece = carousel
    else:
        reels = content.get("reels") or []
        if reels and isinstance(reels[0], dict):
            piece = reels[0]

    if not piece:
        return _assemble_caption("Pure instant coffee. Zero chicory. 100% coffee. ☕", {}, day)

    body = str(piece.get("caption") or piece.get("hook") or "").strip()
    cta  = str(piece.get("cta") or "").strip()
    if cta and cta.lower() not in body.lower():
        body = f"{body}\n\n{cta}"
    return _assemble_caption(body, piece, day)


def _assemble_caption(body: str, piece: dict, day: int = 0) -> str:
    """Append engagement triggers + adaptive 25 hashtags. 2200-char safe."""
    parts = [body]

    comment = str(piece.get("comment_trigger") or "").strip()
    save    = str(piece.get("save_trigger") or "").strip()
    if comment and comment.lower() not in body.lower():
        parts.append(comment)
    if save and save.lower() not in body.lower():
        parts.append(save)

    # Adaptive hashtag bank is primary — the mix evolves with real performance.
    # LLM-generated tags, then the static set, are fallbacks only.
    tags = ""
    try:
        from content_generator.analytics.hashtag_bank import select_hashtags
        tags = select_hashtags(day=day)
    except Exception as e:
        logger.debug("[instagram] adaptive hashtags unavailable: %s", e)
    if not tags:
        llm_tags = piece.get("hashtags")
        if isinstance(llm_tags, list):
            llm_tags = " ".join(str(t) for t in llm_tags)
        tags = str(llm_tags or "").strip() or _FALLBACK_HASHTAGS

    caption = "\n\n".join(p for p in parts if p)
    # Hashtags must survive the 2200-char limit — trim the body, never the tags
    max_body = 2200 - len(tags) - 2
    if len(caption) > max_body:
        caption = caption[:max_body].rsplit(" ", 1)[0]
    return f"{caption}\n\n{tags}"


def _find_carousel_images(content: dict) -> list[str]:
    """Find all carousel slide images generated today."""
    import glob as _glob

    creative_dir = os.getenv("CREATIVE_OUTPUT_DIR", os.path.join("output", "creative"))

    patterns = [
        "carousel_slide_*.jpg",
        "carousel_slide_*.png",
        "slide_*.jpg",
        "slide_*.png",
        "carousel_*.jpg",
        "carousel_*.png",
        "*.jpg",
        "*.png",
    ]

    import datetime as _dt
    today = _dt.date.today().isoformat()

    images = []
    for pattern in patterns:
        images.extend(sorted(_glob.glob(os.path.join(creative_dir, pattern))))

    # Remove duplicates but preserve order; ONLY today's files —
    # creative images persist 7 days in the repo for the publish slots,
    # so without this filter we would post a mix of old days' slides.
    images = [p for p in dict.fromkeys(images) if today in os.path.basename(p)]

    logger.info("[instagram] CREATIVE_OUTPUT_DIR=%s", creative_dir)
    if not images:
        logger.info("[instagram] Images discovered: %s", images)
    else:
        logger.info("[instagram] Found %d images in %s", len(images), creative_dir)

    return images


def _post_single_image(image_path: str, caption: str) -> dict:
    """Upload and publish a single image to Instagram."""
    try:
        import requests
    except ImportError:
        return {"success": False, "media_id": "", "permalink": "", "error": "requests_not_installed"}

    acct_id = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
    token   = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

    # 1. Upload image to get a hosting URL — Instagram requires a publicly accessible URL.
    # We upload to a temporary image host (imgur or use Facebook's own CDN via page photo).
    image_url = _upload_to_public_url(image_path)
    if not image_url:
        return {"success": False, "media_id": "", "permalink": "", "error": "image_upload_failed"}

    try:
        # 2. Create media container (+ product tags if IG Shopping is set up)
        params = {
            "image_url":    image_url,
            "caption":      caption,
            "access_token": token,
        }
        try:
            from content_generator.publisher.product_tags import build_image_product_tags
            tags = build_image_product_tags(caption)
            if tags:
                params["product_tags"] = tags
        except Exception as e:
            logger.debug("[instagram] product tagging skipped: %s", e)
        container_resp = requests.post(
            f"{_GRAPH_API}/{acct_id}/media",
            params=params,
            timeout=30,
        )
        container_data = container_resp.json()
        container_id   = container_data.get("id", "")
        if not container_id:
            err = container_data.get("error", {}).get("message", str(container_data))
            return {"success": False, "media_id": "", "permalink": "", "error": err}

        # 3. Wait for container to be ready
        _wait_for_container(container_id, token)

        # 4. Publish
        return _publish_container(container_id, acct_id, token)

    except Exception as e:
        logger.error("[instagram] Single post error: %s", e)
        return {"success": False, "media_id": "", "permalink": "", "error": str(e)}


def _post_carousel(image_paths: list[str], caption: str) -> dict:
    """Upload and publish a carousel (multi-image) post to Instagram."""
    try:
        import requests
    except ImportError:
        return {"success": False, "media_id": "", "permalink": "", "error": "requests_not_installed"}

    acct_id = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
    token   = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

    # 1. Create individual image containers (carousel items)
    children = []
    for path in image_paths:
        url = _upload_to_public_url(path)
        if not url:
            continue
        try:
            resp = requests.post(
                f"{_GRAPH_API}/{acct_id}/media",
                params={
                    "image_url":    url,
                    "is_carousel_item": True,
                    "access_token": token,
                },
                timeout=30,
            )
            resp_json = resp.json()
            logger.info("[instagram] carousel item upload response: %s", resp_json)
            cid = resp_json.get("id", "")
            if cid:
                children.append(cid)
        except Exception as e:
            logger.debug("[instagram] Carousel item failed: %s", e)

    logger.info("[instagram] child_ids=%s", children)
    if len(children) < 2:
        logger.info("[instagram] Not enough carousel items (%d) — falling back to single", len(children))
        if children:
            return _publish_container(children[0], acct_id, token)
        return {"success": False, "media_id": "", "permalink": "", "error": "carousel_children_failed"}

    # 2. Create carousel container
    try:
        carousel_resp = requests.post(
            f"{_GRAPH_API}/{acct_id}/media",
            params={
                "media_type":   "CAROUSEL",
                "children":     ",".join(children),
                "caption":      caption,
                "access_token": token,
            },
            timeout=30,
        )
        carousel_id = carousel_resp.json().get("id", "")
        if not carousel_id:
            err = carousel_resp.json().get("error", {}).get("message", "carousel_container_failed")
            return {"success": False, "media_id": "", "permalink": "", "error": err}

        _wait_for_container(carousel_id, token)
        return _publish_container(carousel_id, acct_id, token)

    except Exception as e:
        logger.error("[instagram] Carousel post error: %s", e)
        return {"success": False, "media_id": "", "permalink": "", "error": str(e)}


def _publish_container(container_id: str, acct_id: str, token: str) -> dict:
    """Publish a ready media container."""
    try:
        import requests
        resp = requests.post(
            f"{_GRAPH_API}/{acct_id}/media_publish",
            params={"creation_id": container_id, "access_token": token},
            timeout=20,
        )
        data     = resp.json()
        media_id = data.get("id", "")
        if media_id:
            permalink = _get_permalink(media_id, token)
            logger.info("[instagram] Published | id=%s | url=%s", media_id, permalink)
            return {"success": True, "media_id": media_id, "permalink": permalink, "error": None}
        else:
            err = data.get("error", {}).get("message", str(data))
            return {"success": False, "media_id": "", "permalink": "", "error": err}
    except Exception as e:
        return {"success": False, "media_id": "", "permalink": "", "error": str(e)}


def _wait_for_container(container_id: str, token: str, max_wait: int = 60) -> None:
    """Poll container status until FINISHED or timeout."""
    try:
        import requests
        for _ in range(max_wait // 5):
            resp   = requests.get(
                f"{_GRAPH_API}/{container_id}",
                params={"fields": "status_code", "access_token": token},
                timeout=10,
            )
            status = resp.json().get("status_code", "")
            if status == "FINISHED":
                return
            if status == "ERROR":
                logger.warning("[instagram] Container %s errored", container_id)
                return
            time.sleep(5)
    except Exception:
        time.sleep(5)


def _get_permalink(media_id: str, token: str) -> str:
    """Fetch the permanent URL for a published post."""
    try:
        import requests
        resp = requests.get(
            f"{_GRAPH_API}/{media_id}",
            params={"fields": "permalink", "access_token": token},
            timeout=10,
        )
        return resp.json().get("permalink", "")
    except Exception:
        return ""


def _upload_to_public_url(image_path: str) -> str | None:
    """
    Instagram requires a publicly accessible HTTPS URL for image containers.
    We use a temporary image hosting service (Imgbb — free 32MB/image).

    If IMGBB_API_KEY is not set, tries to use the image as a base64 data URL
    via the Graph API's built-in upload (available for some endpoints).

    For production, set IMGBB_API_KEY (free at api.imgbb.com).
    """
    try:
        import requests, base64

        imgbb_key = os.getenv("IMGBB_API_KEY")

        if imgbb_key:
            # Upload to Imgbb — returns a permanent public URL
            with open(image_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")

            resp = requests.post(
                "https://api.imgbb.com/1/upload",
                data={"key": imgbb_key, "image": encoded},
                timeout=30,
            )
            url = resp.json().get("data", {}).get("url", "")
            if url:
                logger.debug("[instagram] Image hosted at: %s", url)
                return url

        # Fallback: try Cloudinary if configured
        cloud_url = _cloudinary_upload(image_path)
        if cloud_url:
            return cloud_url

        logger.warning(
            "[instagram] No image hosting configured. "
            "Set IMGBB_API_KEY (free: api.imgbb.com) to enable image posting."
        )
        return None

    except Exception as e:
        logger.debug("[instagram] Image upload error: %s", e)
        return None


def _cloudinary_upload(image_path: str) -> str | None:
    """Upload to Cloudinary if CLOUDINARY_URL is set (free 25GB/month)."""
    cloud_url = os.getenv("CLOUDINARY_URL")
    if not cloud_url:
        return None
    try:
        import re, requests, base64, hashlib, time as _time
        # Parse cloudinary://api_key:api_secret@cloud_name
        m = re.match(r"cloudinary://(\w+):(\S+)@(\S+)", cloud_url)
        if not m:
            return None
        api_key, api_secret, cloud_name = m.groups()

        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        ts  = str(int(_time.time()))
        sig = hashlib.sha1(f"timestamp={ts}{api_secret}".encode()).hexdigest()

        resp = requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
            data={"file": f"data:image/jpeg;base64,{encoded}",
                  "timestamp": ts, "api_key": api_key, "signature": sig},
            timeout=60,
        )
        return resp.json().get("secure_url", "")
    except Exception:
        return None


def _today() -> str:
    import datetime
    return datetime.date.today().isoformat()
