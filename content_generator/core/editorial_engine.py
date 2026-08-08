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

def resolve_psychology_governance(content: dict) -> dict | None:
    """
    Governance rules for the psychology frame this content was generated under.

    FAILS CLOSED. The earlier form was:

        try:
            frm = get_frame(content["psychology_frame"])
            if frm: gov = frm.get("governance_rules")
        except Exception:
            pass

    so an unknown frame id, a typo, or an import error silently produced
    gov=None and the content proceeded UNGOVERNED — the risk rules vanished at
    exactly the moment something was wrong. A missing frame is now a hard
    rejection, because ungoverned generation is the thing governance exists to
    prevent.

    Returns the rules dict, or raises. None is returned ONLY when the content
    carries no psychology frame at all (legacy assets predating the registry).
    """
    frame_id = content.get("psychology_frame")
    if not frame_id:
        return None
    if str(frame_id).strip().lower() in ("default", "none", "unknown", ""):
        raise EditorialRejectException(
            f"psychology_frame is {frame_id!r} — there is no such frame in the "
            "registry. A placeholder frame means governance was never selected.")
    try:
        from content_generator.core.coffee_psychology import get_frame
        frm = get_frame(frame_id)
    except Exception as e:
        raise EditorialRejectException(
            f"psychology registry unavailable ({e}) — refusing to publish "
            "ungoverned content") from e
    if not frm:
        raise EditorialRejectException(
            f"psychology_frame {frame_id!r} is not in the registry — refusing to "
            "publish ungoverned content")
    return frm.get("governance_rules") or {}


def get_valid_assets(content: dict) -> list[str]:
    """
    Verify which of the generated assets are complete, pass schema validation,
    and meet brand guidelines.
    Returns a list of keys of valid, publishable assets.
    """
    # Resolve governance once, up front. If the frame is missing or bogus this
    # raises and NOTHING is publishable — the correct outcome, since every
    # per-asset brand check below depends on these rules.
    try:
        _governance = resolve_psychology_governance(content)
    except EditorialRejectException as e:
        logger.error("[editorial] %s", e)
        return []

    valid = []
    
    # 1. reel_1
    if "reel_1" in REQUIRED_DAILY_ASSETS:
        try:
            reels = content.get("reels") or []
            reel_1 = reels[0] if len(reels) > 0 else {}
            if reel_1 and isinstance(reel_1, dict) and reel_1.get("hook_text"):
                validate_or_fail(ReelSchema, reel_1)
                is_brand_ok, _ = validate_asset("reel_1", reel_1, _governance)
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
                is_brand_ok, _ = validate_asset("reel_2", reel_2, _governance)
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
                is_brand_ok, _ = validate_asset("carousel", carousel, _governance)
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
                is_brand_ok, _ = validate_asset("instagram_post", ig, _governance)
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
                is_brand_ok, _ = validate_asset("linkedin_post", li, _governance)
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
                is_brand_ok, _ = validate_asset("blog_post", blog, _governance)
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
                is_brand_ok, _ = validate_asset("yt_short", yt, _governance)
                if is_brand_ok:
                    score_data = yt.get("editorial_score", {})
                    score = float(score_data.get("overall", 0))
                    enforce_editorial_gate("yt_short", score)
                    valid.append("yt_short")
        except Exception as e:
            logger.debug("yt_short validation failed: %s", e)
        
    return _apply_growth_director_gates(content, valid)


def _piece_for(content: dict, key: str) -> dict:
    """Map an asset key back to the content piece it was built from."""
    reels = content.get("reels") or []
    if key == "reel_1":
        return reels[0] if len(reels) > 0 and isinstance(reels[0], dict) else {}
    if key == "reel_2":
        return reels[1] if len(reels) > 1 and isinstance(reels[1], dict) else {}
    piece = content.get(key)
    return piece if isinstance(piece, dict) else {}


def _apply_growth_director_gates(content: dict, valid: list[str]) -> list[str]:
    """
    The two Growth Director rules that can veto an otherwise-valid asset:

      NORTH STAR  "If it is not worth sharing privately, it is not worth
                   publishing." An asset can be schema-valid, on-brand and above
                   the editorial threshold and still be generic filler.
      80/20       Product promotion never exceeds 20% of published content.

    Dropping assets here can take the run below MIN_REQUIRED_ASSETS and block
    publishing outright. That is intended: "never publish content simply because
    it fills today's schedule."
    """
    kept = []
    for key in valid:
        piece = _piece_for(content, key)
        if not piece:
            kept.append(key)
            continue
        try:
            from content_generator.core.content_contract import shareability
            share = shareability(piece)
            if not share["passes"]:
                logger.warning(
                    "[editorial] %s REJECTED by north-star gate (%.0f/100): %s",
                    key, share["score"], "; ".join(share["reasons"][:3]))
                continue
        except Exception as e:
            logger.debug("[editorial] shareability check unavailable for %s: %s", key, e)

        try:
            from content_generator.core.content_balance import check as balance_check
            bal = balance_check(piece, key)
            if not bal["allowed"]:
                logger.warning("[editorial] %s REJECTED by 80/20 cap: %s", key, bal["reason"])
                continue
        except Exception as e:
            logger.debug("[editorial] balance check unavailable for %s: %s", key, e)

        kept.append(key)

    dropped = [k for k in valid if k not in kept]
    if dropped:
        logger.warning("[editorial] Growth Director gates dropped %s — quality over schedule",
                       dropped)
    return kept


def approved_assets(content: dict) -> dict:
    """
    THE canonical publish gate. Returns {asset_key: piece} for assets that
    passed EVERY mandatory layer — schema, brand, editorial threshold, the
    north-star shareability gate and the 80/20 cap.

    Schedulers must ask this and publish exactly what comes back. They must not
    call get_valid_assets() and then decide for themselves which object to send:
    that is how an invalid growth_reel got published while the guard was
    checking reel_1, and how "asset invalid -> replace with {} and hope the
    publisher skips it" became a safety boundary.

    Returning the OBJECTS rather than the names removes the second lookup where
    validation and selection could disagree.
    """
    out = {}
    for key in get_valid_assets(content):
        piece = _piece_for(content, key)
        if piece:
            out[key] = piece
    return out


def approved(content: dict, key: str) -> dict | None:
    """One approved asset, or None. Never returns an unvalidated object."""
    return approved_assets(content).get(key)


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
