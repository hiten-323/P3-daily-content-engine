"""
Editorial Engine — enforces 8.0 score threshold, normalizes editorial results,
and performs schema + brand validation audits before publish.
"""
import logging
from content_generator.core.brand_guard import BRAND, REQUIRED_DAILY_ASSETS, MIN_REQUIRED_ASSETS
from content_generator.core.brand_validator import validate_asset
from content_generator.core.schema_validation import (
    ReelSchema, CarouselSchema, InstagramSchema, LinkedinSchema, BlogSchema, YoutubeShortSchema, validate_or_fail
)

logger = logging.getLogger(__name__)

import datetime

class EditorialRejectException(Exception):
    """Raised when an asset fails the editorial threshold."""
    pass


def get_current_pass_score() -> float:
    """
    THE single source of truth for the editorial threshold.

    Order of precedence:
      1. founder policy  quality.minimum_score   (founder-editable, wins)
      2. BRAND.minimum_editorial_score           (brand constitution default)

    Never hardcode a threshold anywhere else — import this function.
    """
    try:
        from content_generator.core.founder_policy import policy
        val = policy().get("minimum_score")
        if val is not None:
            return float(val)
    except Exception as e:
        logger.debug("[editorial] policy threshold unavailable (%s) — using brand default", e)
    return float(BRAND.minimum_editorial_score)


# Backwards-compatible alias for any caller still importing the constant.
# Reads the live value rather than freezing a stale number at import time.
def __getattr__(name):
    if name == "PASS_SCORE":
        return get_current_pass_score()
    raise AttributeError(name)

def normalize_editorial_result(result: dict) -> dict:
    """
    Normalize verdict to PASS/REJECT based on the dynamic score threshold.
    The numeric score is authoritative: verdict always matches score.
    """
    overall = float(result.get("overall", 0.0))
    threshold = get_current_pass_score()
    result["verdict"] = "PASS" if overall >= threshold else "REJECT"
    return result

def enforce_editorial_gate(piece_name: str, score: float) -> bool:
    """
    Raise exception if an asset's score is below threshold.
    """
    threshold = get_current_pass_score()
    if score < threshold:
        raise EditorialRejectException(
            f"Editorial Reject for '{piece_name}': score {score:.1f} below threshold {threshold:.1f}"
        )
    return True

def get_valid_assets(content: dict) -> list[str]:
    """
    Verify which of the generated assets are complete, pass schema validation,
    and meet brand guidelines.
    Returns a list of keys of valid, publishable assets.
    """
    valid = []
    
    # 1. reel_1
    if "reel_1" in REQUIRED_DAILY_ASSETS:
        try:
            reels = content.get("reels") or []
            reel_1 = reels[0] if len(reels) > 0 else {}
            if reel_1 and isinstance(reel_1, dict) and reel_1.get("hook_text"):
                validate_or_fail(ReelSchema, reel_1)
                is_brand_ok, _ = validate_asset("reel_1", reel_1)
                if is_brand_ok:
                    score_data = reel_1.get("editorial_score", {})
                    score = float(score_data.get("overall", 0))
                    enforce_editorial_gate("reel_1", score)
                    valid.append("reel_1")
        except Exception as e:
            logger.debug("reel_1 validation failed: %s", e)
        
    # 2. reel_2
    if "reel_2" in REQUIRED_DAILY_ASSETS:
        try:
            reels = content.get("reels") or []
            reel_2 = reels[1] if len(reels) > 1 else {}
            if reel_2 and isinstance(reel_2, dict) and reel_2.get("hook_text"):
                validate_or_fail(ReelSchema, reel_2)
                is_brand_ok, _ = validate_asset("reel_2", reel_2)
                if is_brand_ok:
                    score_data = reel_2.get("editorial_score", {})
                    score = float(score_data.get("overall", 0))
                    enforce_editorial_gate("reel_2", score)
                    valid.append("reel_2")
        except Exception as e:
            logger.debug("reel_2 validation failed: %s", e)

    # 3. carousel
    if "carousel" in REQUIRED_DAILY_ASSETS:
        try:
            carousel = content.get("carousel") or {}
            if carousel and isinstance(carousel, dict) and carousel.get("title"):
                validate_or_fail(CarouselSchema, carousel)
                is_brand_ok, _ = validate_asset("carousel", carousel)
                if is_brand_ok:
                    score_data = carousel.get("editorial_score", {})
                    score = float(score_data.get("overall", 0))
                    enforce_editorial_gate("carousel", score)
                    valid.append("carousel")
        except Exception as e:
            logger.debug("carousel validation failed: %s", e)

    # 4. instagram_post
    if "instagram_post" in REQUIRED_DAILY_ASSETS:
        try:
            ig = content.get("instagram_post") or {}
            if ig and isinstance(ig, dict) and ig.get("caption"):
                validate_or_fail(InstagramSchema, ig)
                is_brand_ok, _ = validate_asset("instagram_post", ig)
                if is_brand_ok:
                    score_data = ig.get("editorial_score", {})
                    score = float(score_data.get("overall", 0))
                    enforce_editorial_gate("instagram_post", score)
                    valid.append("instagram_post")
        except Exception as e:
            logger.debug("instagram_post validation failed: %s", e)

    # 5. linkedin_post
    if "linkedin_post" in REQUIRED_DAILY_ASSETS:
        try:
            li = content.get("linkedin_post") or {}
            if li and isinstance(li, dict) and li.get("body"):
                validate_or_fail(LinkedinSchema, li)
                is_brand_ok, _ = validate_asset("linkedin_post", li)
                if is_brand_ok:
                    score_data = li.get("editorial_score", {})
                    score = float(score_data.get("overall", 0))
                    enforce_editorial_gate("linkedin_post", score)
                    valid.append("linkedin_post")
        except Exception as e:
            logger.debug("linkedin_post validation failed: %s", e)

    # 6. blog_post
    if "blog_post" in REQUIRED_DAILY_ASSETS:
        try:
            blog = content.get("blog_post") or {}
            if blog and isinstance(blog, dict) and blog.get("body"):
                validate_or_fail(BlogSchema, blog)
                is_brand_ok, _ = validate_asset("blog_post", blog)
                if is_brand_ok:
                    score_data = blog.get("editorial_score", {})
                    score = float(score_data.get("overall", 0))
                    enforce_editorial_gate("blog_post", score)
                    valid.append("blog_post")
        except Exception as e:
            logger.debug("blog_post validation failed: %s", e)

    # 7. yt_short
    if "yt_short" in REQUIRED_DAILY_ASSETS:
        try:
            yt = content.get("yt_short") or {}
            if yt and isinstance(yt, dict):
                validate_or_fail(YoutubeShortSchema, yt)
                is_brand_ok, _ = validate_asset("yt_short", yt)
                if is_brand_ok:
                    score_data = yt.get("editorial_score", {})
                    score = float(score_data.get("overall", 0))
                    enforce_editorial_gate("yt_short", score)
                    valid.append("yt_short")
        except Exception as e:
            logger.debug("yt_short validation failed: %s", e)
        
    return valid

def pre_publish_check(content: dict) -> bool:
    """
    Ensure a minimum number of valid assets are present before publishing.
    Aborts publishing if count is below MIN_REQUIRED_ASSETS.
    """
    valid_assets = get_valid_assets(content)
    logger.info("[editorial] Valid publishable assets found: %s", valid_assets)
    
    if len(valid_assets) < MIN_REQUIRED_ASSETS:
        logger.error(
            """
    PURITY BEANS ENGINE ALERT

    Publish blocked.

    Valid assets:
    %s

    Required:
    %s
            """,
            valid_assets,
            MIN_REQUIRED_ASSETS
        )
        raise RuntimeError(
            f"Publish aborted: Content incomplete. Only {len(valid_assets)} valid assets "
            f"found (required at least {MIN_REQUIRED_ASSETS}): {valid_assets}"
        )
    return True
