"""
Autonomous daily content scheduler.

Full pipeline with health checks, retry, watchdog, and weekly summary:

  05:00  Health check
  05:05  Research (trends + competitors)
  06:00  Generate content
  06:30  Editorial review
  06:45  Assign business objectives
  06:50  Store in semantic memory
  06:55  Save output
  07:00  Nurture dispatch (stalling leads -> WhatsApp/email)
  07:05  Weekly summary (Mondays only)

APScheduler required for daemon mode:  pip install apscheduler
run_now() works without APScheduler for manual / CI use.

Environment variables:
  SCHEDULER_HOUR    (default 6)
  SCHEDULER_MINUTE  (default 0)
  SCHEDULER_TZ      (default Asia/Kolkata)
  ENABLE_EDITORIAL_REVIEW (default true)
  ENABLE_WEEKLY_SUMMARY   (default true)
"""
import logging
import os
import re
import time
import datetime

logger = logging.getLogger(__name__)


# ── Full pipeline ─────────────────────────────────────────────────────────────

def run_full_pipeline(day_number: int = None) -> dict:
    """
    Execute the complete autonomous content pipeline end-to-end.

    Steps: lock -> health -> research -> generate -> editorial -> objectives ->
           memory -> save -> snapshot -> nurture -> founder_report -> summary
    Every step is wrapped in watchdog + retry. One failing step never kills the others.
    """
    from content_generator.scheduler.watchdog import timed_step, timed_step_hard
    from content_generator.scheduler.retry_manager import RetryManager
    from content_generator.scheduler.health_monitor import assert_healthy
    from content_generator.scheduler.run_lock import RunLock

    # ── Run lock — skip if today already ran ──────────────────────────────────
    lock = RunLock()
    lock.__enter__()
    if lock.already_ran:
        logger.info("[scheduler] Today's run already completed — exiting")
        return {"_skipped": True, "reason": "already_ran_today"}

    rm = RetryManager(default_max_retries=2, default_base_wait=30)
    t0 = time.time()

    # Resolve the day number ONCE up front so every path — including the
    # emergency fallback — carries the correct day (not 0).
    if day_number is None:
        from content_generator.rotation import get_day_number
        day_number = get_day_number()

    logger.info("[scheduler] ======= AUTONOMOUS PIPELINE START =======")

    # ── 0. Health check ───────────────────────────────────────────────────────
    with timed_step("health_check", timeout_s=30):
        assert_healthy()

    # ── 0.5 Insights — auto-record yesterday's post performance ──────────────
    # Runs BEFORE generation so today's prompts learn from yesterday's results.
    with timed_step("insights_fetch", timeout_s=60):
        rm.run(
            fn=lambda: _do_fetch_insights(),
            label="insights_fetch",
            max_retries=0,
        )

    # ── 0.6 Revenue attribution — Shopify orders -> post-level learning ──────
    with timed_step("revenue_attribution", timeout_s=60):
        rm.run(
            fn=lambda: _do_revenue_attribution(),
            label="revenue_attribution",
            max_retries=0,
        )

    # ── 1. Research ───────────────────────────────────────────────────────────
    research: dict = {}
    with timed_step("research", timeout_s=120):
        step = rm.run(
            fn=lambda: _do_research(),
            label="research",
            max_retries=1,
        )
        if step.success:
            research = step.value

    # ── 2. Generate (with emergency fallback) ─────────────────────────────────
    from content_generator.pipeline.generator import generate_daily_content, save_content

    content: dict = {}
    with timed_step("content_generation", timeout_s=600):
        step = rm.run(
            fn=lambda: generate_daily_content(day_number=day_number, research_context=research),
            label="content_generation",
            max_retries=2,
            base_wait=60,
        )
        if step.success:
            content = step.value
        else:
            # Emergency fallback — never miss a day
            logger.error("[scheduler] All LLM providers failed — activating emergency fallback")
            from content_generator.scheduler.fallback import emergency_content_set
            content = emergency_content_set(day_number=day_number)

    dn = content.get("day_number", 0)

    # ── 3. Brand injection + editorial review ────────────────────────────────
    _inject_brand_into_content(content, day=dn)
    with timed_step_hard("editorial_review", timeout_s=420):
        rm.run(fn=lambda: _do_editorial(content), label="editorial_review", max_retries=1)

    # ── 4. Business objectives ────────────────────────────────────────────────
    with timed_step("objective_assignment", timeout_s=10):
        step = rm.run(
            fn=lambda: _do_objectives(content, dn),
            label="objective_assignment",
        )
        if step.success and step.value:
            content = step.value

    # ── 5. Semantic memory ────────────────────────────────────────────────────
    with timed_step("memory_store", timeout_s=30):
        rm.run(fn=lambda: _do_memory(content, dn), label="memory_store", max_retries=1)

    # ── 6. Save ───────────────────────────────────────────────────────────────
    filepath = ""
    with timed_step("save_output", timeout_s=30):
        step = rm.run(fn=lambda: save_content(content), label="save_output")
        if step.success:
            filepath = step.value

    # ── 7. Daily snapshot ─────────────────────────────────────────────────────
    with timed_step("snapshot", timeout_s=30):
        rm.run(fn=lambda: _do_snapshot(content, dn), label="snapshot", max_retries=1)

    # ── 7b. Image generation (carousel slides + reel thumbnail) ───────────────
    # Must run BEFORE publish so Instagram/LinkedIn can find the image files.
    with timed_step("image_generation", timeout_s=300):
        rm.run(fn=lambda: _do_generate_images(content, dn), label="image_generation", max_retries=1)

    # ── 8. Nurture dispatch ───────────────────────────────────────────────────
    nurture_result: dict = {}
    with timed_step("nurture_dispatch", timeout_s=120):
        step = rm.run(fn=_do_nurture, label="nurture_dispatch", max_retries=1)
        if step.success:
            nurture_result = step.value or {}

    # ── 9. Publish to all platforms ───────────────────────────────────────────
    publish_result: dict = {}
    with timed_step("publish", timeout_s=300):
        step = rm.run(
            fn=lambda: _do_publish(content, dn),
            label="publish",
            max_retries=1,
        )
        if step.success:
            publish_result = step.value or {}

    # ── 10. Founder WhatsApp report ───────────────────────────────────────────
    with timed_step("founder_report", timeout_s=60):
        rm.run(
            fn=lambda: _do_founder_report(content, nurture_result, publish_result),
            label="founder_report",
        )

    # ── 11. Weekly summary (Mondays only) ─────────────────────────────────────
    _maybe_weekly_summary()

    elapsed = round(time.time() - t0, 1)
    logger.info("[scheduler] ======= DONE in %.1fs -> %s =======", elapsed, filepath)

    # Log retry history
    failed = [h for h in rm.history if not h["success"]]
    if failed:
        logger.warning("[scheduler] Steps that needed retry: %s", [h["label"] for h in failed])

    # Concise DAILY SUMMARY — the human-readable "what happened today" line, so
    # the founder/ops don't have to read 700 log lines.
    try:
        _log_daily_summary(content, publish_result, elapsed, failed)
    except Exception as e:
        logger.debug("[scheduler] daily summary failed: %s", e)

    return content


def _record_quality_telemetry(content: dict, pub: dict, elapsed: float,
                              failed: list, emergency: bool) -> None:
    """Per-run quality metrics (scores, failure rates, latencies) for trending."""
    from content_generator.analytics.telemetry import record_quality

    pieces = [p for p in (content.get("reels") or []) if isinstance(p, dict) and p]
    for key in ("carousel", "instagram_post", "linkedin_post", "blog_post",
                "yt_short", "stories", "growth_reel"):
        p = content.get(key)
        if isinstance(p, dict) and p:
            pieces.append(p)

    scores, confs = [], []
    for p in pieces:
        sc = (p.get("editorial_score") or {}).get("overall")
        if sc is not None:
            scores.append(sc)
        conf = (p.get("audio") or {}).get("confidence")
        if conf is not None:
            confs.append(conf)

    valid, rejects = 0, 0
    try:
        from content_generator.core.editorial_engine import get_valid_assets, get_current_pass_score
        valid = len(get_valid_assets(content))
        threshold = get_current_pass_score()
        rejects = sum(1 for s in scores if float(s) < threshold)
    except Exception as e:
        logger.debug("[telemetry] valid-asset count unavailable: %s", e)

    providers = {}
    try:
        from content_generator.providers.llm_router import get_usage_log
        providers = get_usage_log() or {}
    except Exception as e:
        logger.debug("[telemetry] provider usage unavailable: %s", e)

    publish_ms = sum(int(r.get("duration_ms", 0)) for r in (pub or {}).values()
                     if isinstance(r, dict))

    record_quality(
        day_number=content.get("day_number"),
        generation_ms=max(0, int(elapsed * 1000) - publish_ms),
        publish_ms=publish_ms,
        editorial_scores=scores, confidences=confs,
        assets_generated=len(pieces), assets_valid=valid,
        editorial_rejections=rejects, retries=len(failed or []),
        providers_used=providers, emergency=emergency,
    )


def _log_daily_summary(content: dict, publish_result: dict, elapsed: float, failed: list) -> None:
    """One compact block summarizing the run: providers, publishing, learning."""
    pub = publish_result or {}
    summary = pub.get("summary", "n/a")
    emergency = bool(content.get("_emergency")) or content.get("day_number") == 0 and "emergency" in str(content).lower()

    try:
        _record_quality_telemetry(content, pub, elapsed, failed, emergency)
    except Exception as e:
        logger.debug("[telemetry] quality record skipped: %s", e)

    # Provider usage from the usage log if present
    prov = ""
    try:
        from content_generator.providers.llm_router import get_usage_log
        used = get_usage_log() or {}
        if used:
            prov = ", ".join(f"{k}:{v}" for k, v in list(used.items())[:6])
    except Exception as _e:
        logger.debug("[daily] optional step failed: %s", _e)

    lines = [
        "================= DAILY SUMMARY =================",
        f"Day {content.get('day_number', '?')} | {elapsed:.0f}s"
        + (" | ** EMERGENCY MODE **" if emergency else ""),
        f"Publishing: {summary}",
    ]
    if prov:
        lines.append(f"LLM providers used: {prov}")
    if failed:
        lines.append(f"Steps retried/failed: {', '.join(h['label'] for h in failed)}")
    try:
        from content_generator.core.learning_engine import analyze
        n = analyze().get("count", 0)
        lines.append(f"Learning: {n} posts with performance data so far")
    except Exception as e:
        logger.debug("[summary] learning count unavailable: %s", e)
    try:
        from content_generator.analytics.telemetry import format_report
        lines.append(format_report(7))
    except Exception as e:
        logger.debug("[summary] ops report unavailable: %s", e)
    lines.append("================================================")
    logger.info("\n".join(lines))

    # Engine self-audit — assurance layer that makes regressions visible
    # immediately after any future change.
    try:
        from content_generator.analytics.self_audit import run_self_audit
        run_self_audit(content, pub)
    except Exception as e:
        logger.debug("[summary] self-audit unavailable: %s", e)
    return
    logger.info("\n".join(lines))


# ── Step implementations ──────────────────────────────────────────────────────

def _do_research() -> dict:
    from content_generator.agents.research import run_research
    return run_research()


_QUALITY_MAX_REGEN = int(os.getenv("QUALITY_MAX_REGEN", "1"))   # max regeneration attempts per asset


def _validate_piece_copy(label: str, piece: dict) -> tuple[bool, list[str]]:
    from content_generator.core.brand_validator import validate_asset
    return validate_asset(label, piece)


def _inject_brand_into_piece(label: str, piece: dict) -> dict:
    """
    Ensure brand name and website appear in every text field.
    Appends a natural CTA line only when missing — never duplicates.
    """
    TEXT_FIELDS = {
        "reel_1":         ["caption", "cta"],
        "reel_2":         ["caption", "cta"],
        "carousel":       ["caption", "cta"],
        "instagram_post": ["caption", "cta"],
        "linkedin_post":  ["cta"],
        "blog_post":      ["conclusion"],
        "yt_short":       ["cta", "description"],
    }
    fields = TEXT_FIELDS.get(label, [])
    for field in fields:
        val = piece.get(field)
        if not isinstance(val, str) or not val.strip():
            continue
        low = val.lower()
        needs_brand   = "purity beans" not in low
        needs_website = "p3online.in" not in low
        # Rotate the appended brand line so captions aren't a chicory sermon
        # every day (one-note-messaging fix). Deterministic by piece text.
        line = _brand_tagline(val)
        if needs_brand and needs_website:
            piece[field] = val.rstrip() + f" {line} Shop: https://p3online.in"
        elif needs_brand:
            piece[field] = val.rstrip() + " — Purity Beans"
        elif needs_website:
            piece[field] = val.rstrip() + " Shop: https://p3online.in"

    # CTA field is mandatory on brand-track assets — create it if the LLM skipped it
    if label in ("reel_1", "reel_2", "carousel", "instagram_post") and not str(piece.get("cta", "")).strip():
        piece["cta"] = f"{_brand_tagline(str(piece))} Shop Purity Beans: https://p3online.in"

    # Carousel: the schema requires the FINAL SLIDE to carry brand + website.
    # Injection previously only touched caption/cta, so any carousel whose last
    # slide omitted the link was rejected outright (a silent daily loss).
    if label == "carousel":
        slides = piece.get("slides")
        if isinstance(slides, list) and slides and isinstance(slides[-1], dict):
            last = slides[-1]
            body = str(last.get("body") or "")
            low  = body.lower()
            if "purity beans" not in low:
                body = (body.rstrip() + " Purity Beans.").strip()
            if "p3online.in" not in body.lower():
                body = (body.rstrip() + " Shop: https://p3online.in").strip()
            last["body"] = body
    return piece


# Rotating brand taglines — not every one mentions chicory (one-note fix).
# Every tagline MUST contain a required brand fact (see BRAND_FACT_ALIASES) —
# the tagline is the safety net when the LLM caption omits one, and a tagline
# without a fact fails brand validation and gets the whole asset rejected.
# Framing still varies, and only 2 of 6 mention chicory (no daily sermon).
_BRAND_TAGLINES = (
    "Try Purity Beans — 100% pure coffee.",
    "Purity Beans — pure coffee, nothing added.",
    "Purity Beans — premium instant coffee with no fillers.",
    "Try Purity Beans — zero chicory, 100% coffee.",
    "Purity Beans — pure coffee, the way it should be.",
    "Purity Beans — read the label: no chicory, no fillers.",
)

def _brand_tagline(seed_text: str) -> str:
    return _BRAND_TAGLINES[hash(seed_text) % len(_BRAND_TAGLINES)]


_UNSUPPORTED_STATS = [
    "9 out of 10", "70% of indians", "only 35%", "rs 4,000 crore",
    "studies show", "research shows", "proven by", "clinically",
    "survey says", "according to studies",
]

# Numeric claims we are ALLOWED to make (our own verifiable product facts).
# Everything else numeric about coffee/chicory/the market is unsupported.
_ALLOWED_NUMERIC = re.compile(
    r"\b100\s*%\s*(pure\s+)?coffee|\b100\s*percent\s+coffee|zero\s+chicory|"
    r"\b0\s*%\s*chicory|\b100\s*%\s*pure|\brs\.?\s*\d+\s*(/-)?\s*(per\s+cup|a\s+cup)?",
    re.I,
)
# Any other numeric/statistical claim pattern — fabricated unless whitelisted.
_STAT_PATTERNS = re.compile(
    r"\d+\s*%|"                       # 40%, 40 %
    r"\b\d+\s*(out of|in)\s*\d+\b|"   # 9 out of 10
    r"\b\d+\s*(x|times)\s+(more|less|better|stronger)\b|"
    r"\b(most|majority of|\d+)\s+(people|indians|brands|coffees)\s+(don'?t know|are|have|contain)\b",
    re.I,
)


# Promotional offers the engine must never invent. A live post promised
# "Try your first cup free" — no such campaign exists, which is a false offer
# to customers. Offers may only come from a real campaign, never from the LLM.
_INVENTED_OFFER = re.compile(
    r"\b(first\s+cup\s+free|free\s+(cup|sample|trial|shipping|delivery)|"
    r"\d+\s*%\s*off|flat\s+\d+\s*off|buy\s*\d+\s*get\s*\d+|"
    r"limited[- ]time\s+offer|discount\s+code|coupon)\b",
    re.I,
)


def _strip_invented_offers(text: str) -> str:
    """Remove promotional promises the brand has not actually authorised."""
    if not text:
        return text
    kept = []
    for sentence in re.split(r'(?<=[.!?])\s+', text):
        if _INVENTED_OFFER.search(sentence):
            logger.warning("[brand] stripped invented offer: %r", sentence[:90])
            continue
        kept.append(sentence)
    return " ".join(kept).strip()


def _strip_unsupported_stats(text: str) -> str:
    """
    Remove fabricated statistics.

    Previously this only matched a hardcoded phrase list, so a novel invented
    stat ("40% chicory filler") passed straight through to a live post — a
    false claim about competitor products, which is both a policy violation
    and a real regulatory risk for a food brand. Now any numeric/statistical
    claim is stripped unless it is one of our own verifiable facts
    (100% coffee, zero chicory, price per cup).
    """
    if not text:
        return text

    # 1. legacy exact phrases
    low = text.lower()
    for stat in _UNSUPPORTED_STATS:
        if stat in low:
            text = re.sub(r'[^.!?]*' + re.escape(stat) + r'[^.!?]*[.!?]',
                          '', text, flags=re.IGNORECASE).strip()

    # 2. pattern-based: drop any sentence carrying a non-whitelisted number claim
    kept = []
    for sentence in re.split(r'(?<=[.!?])\s+', text):
        if _STAT_PATTERNS.search(sentence) and not _ALLOWED_NUMERIC.search(sentence):
            logger.warning("[brand] stripped unsupported statistic: %r", sentence[:90])
            continue
        kept.append(sentence)
    return " ".join(kept).strip()


_DEFAULT_HASHTAGS = (
    "#PurityBeans #PureCoffee #InstantCoffee #NoCicory #CoffeeLover "
    "#IndianCoffee #CoffeeIndia #MadeInIndia #PremiumCoffee #FreezeDriedCoffee "
    "#GourmetCoffee #CoffeeCommunity #CoffeeAddict #CoffeeGram #CoffeeCulture "
    "#SupportIndianBrands #IndianBrands #PurityBeansCoffee #BrewPure #PureCoffeeExperience "
    "#MorningCoffee #CoffeeTime #CoffeeDaily #CoffeeLife #CoffeeLove"
)

_DEFAULT_COMMENT = "Comment COFFEE below if you refuse to drink chicory disguised as coffee."
_DEFAULT_SAVE    = "Save this before your next grocery run — real coffee matters."
_DEFAULT_SHARE   = "Share with someone who starts every morning with coffee."


def _ensure_engagement_fields(piece: dict) -> None:
    """
    Auto-fill mandatory engagement fields.

    Fields must not just EXIST — the schema enforces min_length=10, so a short
    LLM answer like "Share it" (8 chars) fails validation and sinks the whole
    asset. Anything present-but-too-short is replaced with the default.
    """
    for field, default, min_len in (
        ("hashtags",        _DEFAULT_HASHTAGS, 10),
        ("comment_trigger", _DEFAULT_COMMENT,  10),
        ("save_trigger",    _DEFAULT_SAVE,     10),
        ("share_trigger",   _DEFAULT_SHARE,    10),
    ):
        val = piece.get(field)
        if not isinstance(val, str) or len(val.strip()) < min_len:
            if val:
                logger.debug("[brand] %s too short (%r) — using default", field, val)
            piece[field] = default


def _ensure_captions(content: dict) -> None:
    """
    Auto-fill missing caption fields before validation.
    Reel: derive from last frame spoken text.
    Carousel: derive from title + CTA.
    """
    reels = content.get("reels") or []
    for reel in reels:
        if not isinstance(reel, dict):
            continue
        if not reel.get("caption"):
            frames = reel.get("frames") or []
            spoken_lines = [f.get("spoken", "") for f in frames if isinstance(f, dict) and f.get("spoken")]
            if spoken_lines:
                reel["caption"] = spoken_lines[-1]
            else:
                reel["caption"] = f"Purity Beans — 100% coffee, zero chicory. Order at p3online.in"

    carousel = content.get("carousel")
    if isinstance(carousel, dict) and carousel and not carousel.get("caption"):
        title = carousel.get("title", "Pure Coffee")
        carousel["caption"] = (
            f"{title} — Purity Beans. 100% coffee, zero chicory. "
            f"India's cleanest instant coffee. Shop at p3online.in"
        )


def _inject_jar_creative_into_reels(content: dict, day: int) -> None:
    """
    For every reel that does not already have ai_image_hook_prompt / ai_video_motion_prompt,
    generate them using the actual jar images via jar_composer.
    This ensures every reel output has paste-ready Nano Banana Pro + Seedance prompts.
    """
    try:
        from content_generator.creative.jar_composer import build_reel_hook_prompt, get_jar_paths_for_content
    except Exception:
        return

    reels = content.get("reels") or []
    for i, reel in enumerate(reels):
        if not isinstance(reel, dict):
            continue
        # Only inject if the LLM did not already produce these fields
        if reel.get("ai_image_hook_prompt") and reel.get("ai_video_motion_prompt"):
            continue
        try:
            hook_package = build_reel_hook_prompt(day=day + i)
            reel["ai_image_hook_prompt"]    = hook_package["image_prompt"]
            reel["ai_video_motion_prompt"]  = hook_package["motion_prompt"]
            reel["reference_jar_paths"]     = hook_package["reference_jar_paths"]
            reel["hook_visual_concept"]     = hook_package["concept"]
            reel.setdefault("hook_text_overlay", hook_package["hook_text"])
            logger.info("[creative] Jar hook prompts injected into reel_%d", i + 1)
        except Exception as e:
            logger.warning("[creative] Could not inject jar hook into reel_%d: %s", i + 1, e)


# The LLM sometimes echoes the prompt's scaffolding into the copy itself
# ("Slide 1: ...", "Frame 2 -", "Hook:"). Rendered into an image it looks like
# a leaked template. Strip these labels from anything that becomes on-screen text.
_SCAFFOLD_PREFIX = re.compile(
    r"^\s*(slide|frame|scene|step|part|hook|headline|caption|title)\s*"
    r"(no\.?\s*)?\d*\s*[:\-–—.)]\s*",
    re.I,
)


def _clean_scaffolding(text: str) -> str:
    """Remove leading 'Slide 1:' / 'Frame 2 -' style labels (repeatedly)."""
    if not isinstance(text, str):
        return text
    cleaned = text.strip()
    for _ in range(3):                       # handles "Slide 1: Hook: ..."
        new = _SCAFFOLD_PREFIX.sub("", cleaned).strip()
        if new == cleaned:
            break
        cleaned = new
    return cleaned


def _strip_scaffolding_everywhere(content: dict) -> None:
    """Clean every field that can end up as on-screen text or a headline."""
    def _clean_piece(piece: dict) -> None:
        if not isinstance(piece, dict):
            return
        for f in ("hook_text", "chosen_hook", "hook", "headline", "title",
                  "hook_spoken", "alt_hook", "hook_text_overlay"):
            if isinstance(piece.get(f), str):
                piece[f] = _clean_scaffolding(piece[f])
        for lst in ("frames", "script", "slides", "scenes"):
            for item in (piece.get(lst) or []):
                if isinstance(item, dict):
                    for f in ("on_screen", "heading", "headline", "spoken", "body"):
                        if isinstance(item.get(f), str):
                            item[f] = _clean_scaffolding(item[f])

    for reel in (content.get("reels") or []):
        _clean_piece(reel)
    for key in ("carousel", "instagram_post", "growth_reel", "yt_short", "stories"):
        piece = content.get(key)
        _clean_piece(piece)
        if key == "stories" and isinstance(piece, dict):
            for sub in piece.values():
                _clean_piece(sub)


def _inject_brand_into_content(content: dict, day: int = 0) -> None:
    """Run caption fill + engagement field fill + brand injection + stat scrubbing."""
    _strip_scaffolding_everywhere(content)
    _ensure_captions(content)
    _inject_jar_creative_into_reels(content, day)

    # Decision layer: attach per-asset metadata (Company Memory records +
    # campaign/experiment/playbook) so every published asset carries reasoning
    try:
        from content_generator.intelligence.decision_layer import attach_asset_metadata
        attach_asset_metadata(content, day)
    except Exception as e:
        logger.debug("[creative] asset metadata skipped: %s", e)

    # Hook A/B: score all hook candidates, publish only the winner
    try:
        from content_generator.analytics.hook_selector import run_hook_ab
        run_hook_ab(content)
    except Exception as e:
        logger.warning("[creative] hook A/B skipped: %s", e)

    # Audio Director: attach a per-asset audio plan (auto-embed track + in-app
    # trending-audio recommendation for the manual posting path)
    try:
        from content_generator.creative.audio_director import get_audio_plan
        for reel in content.get("reels") or []:
            if isinstance(reel, dict) and reel:
                hook = str(reel.get("hook_text") or reel.get("caption") or "")
                reel["audio"] = get_audio_plan(hook, day)
        for key in ("growth_reel", "stories", "yt_short"):
            piece = content.get(key)
            if isinstance(piece, dict) and piece:
                txt = str(piece.get("chosen_hook") or piece.get("hook") or piece.get("title") or "")
                piece["audio"] = get_audio_plan(txt, day)
    except Exception as e:
        logger.warning("[creative] audio director skipped: %s", e)

    reels = content.get("reels") or []
    for i, label in enumerate(["reel_1", "reel_2"]):
        if i < len(reels) and isinstance(reels[i], dict):
            _ensure_engagement_fields(reels[i])
            _inject_brand_into_piece(label, reels[i])

    for label in ("carousel", "instagram_post", "linkedin_post", "blog_post", "yt_short"):
        piece = content.get(label)
        if isinstance(piece, dict) and piece:
            _ensure_engagement_fields(piece)
            _inject_brand_into_piece(label, piece)
            for field in ("caption", "body", "introduction", "conclusion", "hook", "script"):
                if isinstance(piece.get(field), str):
                    piece[field] = _strip_invented_offers(
                        _strip_unsupported_stats(piece[field]))


def _do_editorial(content: dict) -> None:
    """
    Review each content piece. Regenerates up to QUALITY_MAX_REGEN times.
    Skips LLM review entirely if all providers are exhausted (circuit open).
    """
    from content_generator.agents.editorial import review_content
    from content_generator.core.editorial_engine import normalize_editorial_result, get_current_pass_score
    from content_generator.providers import llm_router

    providers_ok = llm_router.any_provider_available()
    if not providers_ok:
        logger.warning("[editorial] All providers exhausted — skipping LLM review, accepting content as-is")
        return

    review_targets = [
        ("reel_1",         "reels",         0),
        ("reel_2",         "reels",         1),
        ("carousel",       "carousel",      None),
        ("instagram_post", "instagram_post", None),
        ("linkedin_post",  "linkedin_post",  None),
        ("blog_post",      "blog_post",      None),
    ]

    threshold = get_current_pass_score()

    for label, key, idx in review_targets:
        # Extract piece
        if idx is not None:
            pieces = content.get(key) or []
            piece  = pieces[idx] if len(pieces) > idx else {}
        else:
            piece  = content.get(key) or {}

        if not isinstance(piece, dict) or not piece:
            continue

        for attempt in range(_QUALITY_MAX_REGEN + 1):
            is_copy_ok, copy_issues = _validate_piece_copy(label, piece)
            
            if is_copy_ok:
                review = review_content(piece, label=label)
                review = normalize_editorial_result(review)
                piece["editorial_score"] = review
                score  = review.get("overall", 0)
                verdict = review.get("verdict", "")

                if verdict == "PASS":
                    logger.info("[editorial] %s PASS — score %.1f (threshold %.1f)", label, score, threshold)
                    break

                feedback = review.get("feedback", "")
                logger.warning(
                    "[editorial] %s REJECT — score %.1f | feedback: %s | attempt %d/%d",
                    label, score, feedback, attempt + 1, _QUALITY_MAX_REGEN + 1,
                )
            else:
                feedback = f"Brand copy validation failed: {copy_issues}"
                piece["editorial_score"] = {
                    "overall": 0.0,
                    "verdict": "REJECT",
                    "feedback": feedback
                }
                logger.warning(
                    "[editorial] %s REJECT (Brand validation failed) | issues: %s | attempt %d/%d",
                    label, copy_issues, attempt + 1, _QUALITY_MAX_REGEN + 1,
                )

            if attempt < _QUALITY_MAX_REGEN:
                logger.info("[editorial] Regenerating %s (attempt %d)...", label, attempt + 2)
                improved = _regenerate_piece(label, piece, feedback, content)
                if improved:
                    # Replace in content dict
                    if idx is not None:
                        content[key][idx] = improved
                        piece = improved
                    else:
                        content[key] = improved
                        piece = improved
                else:
                    logger.warning("[editorial] Regeneration failed for %s — keeping original", label)
                    break
            else:
                logger.warning(
                    "[editorial] %s final score below threshold %.1f — keeping as is (will be filtered before publishing)",
                    label, threshold,
                )


def _regenerate_piece(label: str, piece: dict, feedback: str, content: dict) -> dict | None:
    """
    Regenerate a single content piece using the original generator with feedback context.
    Returns improved piece dict, or None if regeneration fails.
    """
    try:
        from content_generator.providers.llm_router import call as llm_call
        from content_generator.prompts.brand import brand_block
        from content_generator.core.editorial_engine import get_current_pass_score

        threshold = get_current_pass_score()
        piece_json = str(piece)[:800]
        regen_prompt = (
            f"{brand_block()}\n\n"
            f"TASK: Improve this content piece. It was rejected (score too low).\n\n"
            f"ORIGINAL PIECE ({label}):\n{piece_json}\n\n"
            f"REJECTION FEEDBACK:\n{feedback}\n\n"
            f"REQUIREMENTS:\n"
            f"- Score must be {threshold} or higher\n"
            f"- Keep the same format/structure as the original\n"
            f"- Fix the specific issues mentioned in the feedback\n"
            f"- More scroll-stopping hook, stronger CTA, clearer value\n\n"
            f"Return ONLY the improved JSON object (same keys as original)."
        )
        result = llm_call(regen_prompt, label=f"regen_{label}", max_tokens=1500)
        if isinstance(result, dict) and result:
            logger.info("[editorial] Regeneration successful for %s", label)
            return result
    except Exception as e:
        logger.warning("[editorial] Regeneration error for %s: %s", label, e)
    return None


def _do_objectives(content: dict, dn: int) -> dict:
    from content_generator.objectives.mapper import assign_all
    return assign_all(content, dn)


def _do_memory(content: dict, dn: int) -> None:
    from content_generator.memory.semantic import store_content
    pieces = {
        f"reel_1_day{dn}":   content.get("reels", [{}])[0] if content.get("reels") else {},
        f"reel_2_day{dn}":   (content.get("reels", [{}, {}]) + [{}])[1],
        f"carousel_day{dn}": content.get("carousel", {}),
        f"linkedin_day{dn}": content.get("linkedin_post", {}),
        f"blog_day{dn}":     content.get("blog_post", {}),
    }
    for cid, piece in pieces.items():
        if piece and isinstance(piece, dict):
            store_content(cid, piece)


def _do_snapshot(content: dict, day_number: int) -> str:
    from content_generator.scheduler.snapshot import save_daily_snapshot
    return save_daily_snapshot(content=content, day_number=day_number)


def _do_generate_images(content: dict, day_number: int) -> dict:
    """
    Generate actual image files from AI prompts in the content dict.
    Saves carousel slides and reel thumbnail to output/creative/.
    These files are then found by instagram.py and linkedin.py publishers.
    """
    # Brand images are composed from REAL jar photos (brand_assets/*.png).
    # Text-to-image AI cannot see reference images and invents fake jars with
    # gibberish labels — so AI generation is only the fallback, never primary.
    from content_generator.creative.real_jar_composer import (
        compose_carousel_slides,
        compose_reel_thumbnail,
    )

    results = {"carousel": [], "reel": None}

    # Carousel slides — one real jar photo per slide, rotating daily
    carousel = content.get("carousel") or {}
    slides   = carousel.get("slides") or []
    if slides:
        paths = compose_carousel_slides(slides, day_number)

        # Quality tier: Gemini places the REAL jar into a cinematic scene for
        # the cover slide (label preserved). Card version replaced on success.
        try:
            from content_generator.creative.gemini_scene import generate_scene_with_real_jar
            first = slides[0] if isinstance(slides[0], dict) else {}
            scene = (first.get("visual")
                     or "dark marble kitchen counter at dawn, warm golden side light, "
                        "soft steam rising from a cup beside the jar, deep shadows, "
                        "premium editorial FMCG photography")
            cover = generate_scene_with_real_jar(
                scene, day=day_number, idx=0,
                label=f"carousel_slide_1_day{day_number}_scene",
            )
            if cover and paths:
                paths[0] = cover
                logger.info("[images] Carousel cover upgraded to Gemini scene")
        except Exception as e:
            logger.debug("[images] Gemini cover skipped: %s", e)

        results["carousel"] = paths
        logger.info("[images] Composed %d carousel slides from real jar photos", len(paths))

    if not results["carousel"]:
        # Fallback: AI generation (may not match the real jar)
        try:
            from content_generator.creative.flux_generator import generate_carousel_images
            paths = generate_carousel_images(slides, day_number) if slides else []
            results["carousel"] = paths
            logger.warning("[images] Fell back to AI-generated carousel (%d slides)", len(paths))
        except Exception as e:
            logger.error("[images] Carousel image fallback failed: %s", e)

    # Reel thumbnail — Gemini scene with real jar first, card composer fallback
    reel = content.get("reels", [{}])[0] if content.get("reels") else {}
    if reel:
        path = None
        try:
            from content_generator.creative.gemini_scene import generate_scene_with_real_jar
            scene = (reel.get("hook_visual_concept")
                     or reel.get("visual_direction")
                     or "dramatic dark studio, single warm gold beam on the jar, "
                        "coffee granules scattered on black marble, faint steam")
            path = generate_scene_with_real_jar(
                str(scene)[:400], day=day_number, idx=7,
                label=f"reel_1_thumb_day{day_number}",
            )
        except Exception as e:
            logger.debug("[images] Gemini reel thumb skipped: %s", e)
        if not path:
            path = compose_reel_thumbnail(reel, day_number, label="reel_1")
        if not path:
            try:
                from content_generator.creative.flux_generator import generate_reel_thumbnail
                path = generate_reel_thumbnail(reel, day_number, label="reel_1")
            except Exception:
                path = None
        results["reel"] = path
        if path:
            logger.info("[images] Reel thumbnail: %s", path)

    # UGC + Avatar + Reel Hook — jar-reference creative package
    try:
        from content_generator.creative.ugc_generator import generate_daily_ugc
        ugc_result = generate_daily_ugc(day=day_number)
        results["ugc_package"] = ugc_result
        brief = ugc_result.get("tool_brief_path")
        logger.info("[images] UGC creative package generated. Tool brief: %s", brief)
    except Exception as e:
        logger.warning("[images] UGC generation failed (non-blocking): %s", e)
        results["ugc_package"] = None

    return results


def _best_assets_by_score(content: dict, count: int) -> list[str]:
    """Return top N assets ranked by editorial score — emergency fallback."""
    ASSET_MAP = {
        "reel_1":         ("reels", 0),
        "reel_2":         ("reels", 1),
        "carousel":       ("carousel", None),
        "instagram_post": ("instagram_post", None),
        "linkedin_post":  ("linkedin_post", None),
        "blog_post":      ("blog_post", None),
        "yt_short":       ("yt_short", None),
    }
    scored = []
    for label, (key, idx) in ASSET_MAP.items():
        if idx is not None:
            pieces = content.get(key) or []
            piece = pieces[idx] if len(pieces) > idx else {}
        else:
            piece = content.get(key) or {}
        if isinstance(piece, dict) and piece:
            score = float((piece.get("editorial_score") or {}).get("overall", 0))
            scored.append((score, label))
    scored.sort(reverse=True)
    return [label for _, label in scored[:count]]


def _do_fetch_insights() -> dict:
    """Fetch yesterday's Instagram metrics and feed the learning engine. Non-blocking."""
    # Version Manager: record the active policy version (audit trail)
    try:
        from content_generator.core.founder_policy import record_policy_version
        record_policy_version()
    except Exception as e:
        logger.debug("[policy] version record skipped: %s", e)
    from content_generator.analytics.insights_fetcher import fetch_pending_insights
    return fetch_pending_insights()


def _do_revenue_attribution() -> dict:
    """Pull Shopify orders, attribute Instagram revenue to posts. Non-blocking."""
    from content_generator.analytics.revenue_attribution import run_revenue_attribution
    return run_revenue_attribution()


def _do_publish(content: dict, day_number: int) -> dict:
    """Post today's content, filtering out any invalid/failed assets."""
    from content_generator.core.editorial_engine import get_valid_assets
    from content_generator.core.brand_guard import MIN_REQUIRED_ASSETS

    # Founder policy: auto_publish=false => generate + save only (dry run)
    try:
        from content_generator.core.founder_policy import policy
        if not policy().get("auto_publish", True):
            logger.warning("[publish] auto_publish=false in founder_policies.yaml — "
                           "content generated and saved but NOT posted")
            return {"skipped": True, "reason": "auto_publish_disabled",
                    "published_platforms": [], "summary": "Dry run (auto_publish off)"}
    except Exception as _e:
        logger.debug("[daily] optional step failed: %s", _e)

    # 1. Get validated assets
    valid_assets = get_valid_assets(content)
    logger.info("[editorial] Valid publishable assets found: %s", valid_assets)

    # 2. Emergency fallback — never miss a day
    if len(valid_assets) < MIN_REQUIRED_ASSETS:
        logger.warning(
            "[publish] Only %d valid assets (need %d) — activating emergency fallback: "
            "publishing top %d by score", len(valid_assets), MIN_REQUIRED_ASSETS, MIN_REQUIRED_ASSETS
        )
        valid_assets = _best_assets_by_score(content, MIN_REQUIRED_ASSETS)
    filtered_content = content.copy()
    
    if "reel_1" not in valid_assets:
        if filtered_content.get("reels"):
            filtered_content["reels"][0] = {}
    if "reel_2" not in valid_assets:
        if filtered_content.get("reels") and len(filtered_content["reels"]) > 1:
            filtered_content["reels"][1] = {}
    if "carousel" not in valid_assets:
        filtered_content["carousel"] = {}
    if "instagram_post" not in valid_assets:
        filtered_content["instagram_post"] = {}
    if "linkedin_post" not in valid_assets:
        filtered_content["linkedin_post"] = {}
    if "blog_post" not in valid_assets:
        filtered_content["blog_post"] = {}
    if "yt_short" not in valid_assets:
        filtered_content["yt_short"] = {}

    from content_generator.publisher.dispatcher import publish_all
    result = publish_all(filtered_content, day_number=day_number)

    # Track published Instagram media so the insights fetcher can auto-record
    # its performance tomorrow and feed the learning engine.
    try:
        ig = result.get("instagram") or {}
        if ig.get("success") and ig.get("media_id"):
            from content_generator.analytics.insights_fetcher import track_published_post
            piece = filtered_content.get("carousel") or {}
            if not piece.get("caption"):
                reels = filtered_content.get("reels") or [{}]
                piece = reels[0] if reels and isinstance(reels[0], dict) else {}
            track_published_post(
                media_id    = ig["media_id"],
                asset_id    = f"instagram_day{day_number}",
                track       = "brand",
                hook        = str(piece.get("hook_text") or piece.get("title") or "")[:120],
                topic       = str(piece.get("save_mechanic") or piece.get("hook_archetype") or "")[:120],
                format_used = "carousel" if filtered_content.get("carousel", {}).get("caption") else "single_image",
                hashtags    = str(ig.get("hashtags_used") or ""),
            )
    except Exception as e:
        logger.warning("[publish] Could not track published post for insights: %s", e)

    return result


def _do_founder_report(content: dict, nurture_result: dict, publish_result: dict = None) -> bool:
    from content_generator.scheduler.founder_report import send_founder_report
    pipeline = {**(nurture_result or {}), "publish": publish_result or {}}
    return send_founder_report(content=content, pipeline_result=pipeline)


def _do_nurture() -> dict:
    """
    Daily nurture step — find stalling leads and send follow-up messages.

    Strategy:
      1. Fetch all stalling leads (stuck beyond STAGE_MAX_DAYS for their segment/stage)
      2. Check nurture_log — skip leads messaged in the last 3 days (avoid spam)
      3. Dispatch WhatsApp (if phone) or email (if @) via template for their stage
      4. Return summary of dispatched messages

    Runs whether or not WhatsApp/SMTP are configured — degrades to log-only.
    """
    from content_generator.leads.lead_capture import get_stalling_leads
    from content_generator.nurture.whatsapp import dispatch_nurture_batch
    from content_generator.nurture.email_sequences import dispatch_email_batch

    stalling = get_stalling_leads()
    if not stalling:
        logger.info("[nurture] No stalling leads — nothing to dispatch")
        return {"dispatched": 0, "stalling": 0}

    # Filter to leads not already nurtured in last 3 days
    eligible = _filter_recently_nurtured(stalling, cooldown_days=3)
    if not eligible:
        logger.info(
            "[nurture] %d stalling leads but all nurtured recently — skipping",
            len(stalling),
        )
        return {"dispatched": 0, "stalling": len(stalling)}

    logger.info("[nurture] Dispatching to %d stalling leads", len(eligible))

    # WhatsApp for phone numbers, email for @-addresses
    wa_results    = dispatch_nurture_batch(eligible)
    email_results = dispatch_email_batch(eligible)

    total = len([r for r in wa_results + email_results if r.get("success")])
    logger.info("[nurture] Dispatched %d messages to %d leads", total, len(eligible))
    return {"dispatched": total, "stalling": len(stalling), "eligible": len(eligible)}


def _filter_recently_nurtured(leads: list[dict], cooldown_days: int = 3) -> list[dict]:
    """Remove leads that already received a nurture message within cooldown_days."""
    try:
        from content_generator.analytics.metrics_store import _ensure_init, _conn
        _ensure_init()
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=cooldown_days)).isoformat()
        with _conn() as con:
            rows = con.execute(
                "SELECT DISTINCT lead_id FROM nurture_log WHERE created_at >= ?",
                (cutoff,),
            ).fetchall()
        recent_ids = {r["lead_id"] for r in rows}
        return [l for l in leads if l.get("lead_id") not in recent_ids]
    except Exception as e:
        logger.debug("[nurture] filter_recently_nurtured failed: %s — using all", e)
        return leads


def _maybe_weekly_summary() -> None:
    if os.getenv("ENABLE_WEEKLY_SUMMARY", "true").lower() != "true":
        return
    if datetime.date.today().weekday() != 0:   # 0 = Monday
        return
    try:
        from content_generator.dashboard.weekly_summary import generate_weekly_summary
        generate_weekly_summary(days=7)
    except Exception as e:
        logger.warning("[scheduler] Weekly summary failed: %s", e)
    try:
        # Auto-refresh brand equity signals (Trends, UGC hashtag, comment
        # sentiment) BEFORE the brief so it reports fresh numbers
        from content_generator.analytics.brand_signals import update_brand_equity_inputs
        update_brand_equity_inputs()
    except Exception as e:
        logger.warning("[scheduler] Brand signals update failed: %s", e)
    try:
        from content_generator.analytics.founder_brief import generate_founder_brief
        generate_founder_brief()
    except Exception as e:
        logger.warning("[scheduler] Founder brief failed: %s", e)


# ── Manual trigger ────────────────────────────────────────────────────────────

def run_now(day_number: int = None) -> dict:
    """Run the full pipeline immediately. Useful for testing and CI."""
    return run_full_pipeline(day_number=day_number)


# ── APScheduler daemon ────────────────────────────────────────────────────────

def start_scheduler() -> None:
    """
    Start the APScheduler blocking daemon.
    Runs daily at SCHEDULER_HOUR:SCHEDULER_MINUTE IST.
    Requires:  pip install apscheduler
    """
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error(
            "[scheduler] APScheduler not installed.\n"
            "  pip install apscheduler\n"
            "  Then retry."
        )
        return

    hour   = int(os.getenv("SCHEDULER_HOUR",   "6"))
    minute = int(os.getenv("SCHEDULER_MINUTE", "0"))
    tz     = os.getenv("SCHEDULER_TZ", "Asia/Kolkata")

    scheduler = BlockingScheduler(timezone=tz)
    scheduler.add_job(
        run_full_pipeline,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
        id="daily_content",
        name="Purity Beans daily pipeline",
        misfire_grace_time=600,
        replace_existing=True,
    )

    logger.info(
        "[scheduler] Daemon started — runs daily at %02d:%02d %s",
        hour, minute, tz,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("[scheduler] Daemon stopped.")


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from content_generator import configure
    configure(load_env=True, setup_logging=True)

    if "--now" in sys.argv:
        import json
        from content_generator.scheduler.slots import slots_enabled, get_current_slot, run_publish_slot
        # --day N regenerates a specific day. run_now/run_full_pipeline have
        # accepted day_number all along; nothing ever parsed it, so the
        # workflow's day_number input was collected and silently discarded —
        # the operator believed a day had been regenerated when it had not.
        _day = None
        if "--day" in sys.argv:
            _i = sys.argv.index("--day")
            if _i + 1 < len(sys.argv):
                try:
                    _day = int(sys.argv[_i + 1])
                except ValueError:
                    sys.exit(f"--day expects an integer, got {sys.argv[_i + 1]!r}")
            else:
                sys.exit("--day requires a number")

        slot = get_current_slot() if slots_enabled() else "generate"
        if slot == "generate":
            result = run_now(day_number=_day)
        else:
            # Publish-only slot: post this morning's content at its optimal window
            result = run_publish_slot(slot)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif "--report" in sys.argv:
        from content_generator.dashboard.reports import print_report
        print_report(days=7)
    elif "--weekly" in sys.argv:
        from content_generator.dashboard.weekly_summary import generate_weekly_summary
        generate_weekly_summary()
    elif "--health" in sys.argv:
        from content_generator.scheduler.health_monitor import get_health_report
        import json
        print(json.dumps(get_health_report(), indent=2))
    elif "--unlock" in sys.argv:
        # Emergency: clear a stuck run lock so next invocation runs
        from content_generator.scheduler.run_lock import RunLock
        RunLock.force_clear()
        print("Run lock cleared.")
    elif "--snapshots" in sys.argv:
        from content_generator.scheduler.snapshot import list_snapshots
        for s in list_snapshots(limit=10):
            print(s)
    else:
        start_scheduler()
