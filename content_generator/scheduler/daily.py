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

    logger.info("[scheduler] ======= AUTONOMOUS PIPELINE START =======")

    # ── 0. Health check ───────────────────────────────────────────────────────
    with timed_step("health_check", timeout_s=30):
        assert_healthy()

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
            content = emergency_content_set(day_number=day_number or 0)

    dn = content.get("day_number", 0)

    # ── 3. Editorial review (hard timeout — Gemini 429 loops can run forever) ──
    with timed_step_hard("editorial_review", timeout_s=180):
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

    return content


# ── Step implementations ──────────────────────────────────────────────────────

def _do_research() -> dict:
    from content_generator.agents.research import run_research
    return run_research()


_QUALITY_THRESHOLD = float(os.getenv("QUALITY_THRESHOLD", "7.0"))
_QUALITY_MAX_REGEN = int(os.getenv("QUALITY_MAX_REGEN", "2"))   # max regeneration attempts


def _do_editorial(content: dict) -> None:
    """
    Review each content piece. If score < QUALITY_THRESHOLD (default 7.0),
    attempt regeneration up to QUALITY_MAX_REGEN times before accepting.
    """
    from content_generator.agents.editorial import review_content

    review_targets = [
        ("reel_1",         "reels",         0),
        ("reel_2",         "reels",         1),
        ("carousel",       "carousel",      None),
        ("instagram_post", "instagram_post", None),
    ]

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
            review = review_content(piece, label=label)
            piece["editorial_score"] = review
            score  = review.get("overall", 0)
            verdict = review.get("verdict", "")

            if score >= _QUALITY_THRESHOLD:
                logger.info("[editorial] %s PASS — score %.1f", label, score)
                break

            feedback = review.get("feedback", "")
            logger.warning(
                "[editorial] %s REJECT — score %.1f | feedback: %s | attempt %d/%d",
                label, score, feedback, attempt + 1, _QUALITY_MAX_REGEN + 1,
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
                    "[editorial] %s final score %.1f below threshold %.1f — publishing anyway",
                    label, score, _QUALITY_THRESHOLD,
                )


def _regenerate_piece(label: str, piece: dict, feedback: str, content: dict) -> dict | None:
    """
    Regenerate a single content piece using the original generator with feedback context.
    Returns improved piece dict, or None if regeneration fails.
    """
    try:
        from content_generator.providers.llm_router import call as llm_call
        from content_generator.prompts.brand import brand_block

        piece_json = str(piece)[:800]
        regen_prompt = (
            f"{brand_block()}\n\n"
            f"TASK: Improve this content piece. It was rejected (score too low).\n\n"
            f"ORIGINAL PIECE ({label}):\n{piece_json}\n\n"
            f"REJECTION FEEDBACK:\n{feedback}\n\n"
            f"REQUIREMENTS:\n"
            f"- Score must be 7.0 or higher\n"
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
    from content_generator.creative.flux_generator import (
        generate_carousel_images,
        generate_reel_thumbnail,
    )

    results = {"carousel": [], "reel": None}

    # Carousel slides
    carousel = content.get("carousel") or {}
    slides   = carousel.get("slides") or []
    if slides:
        paths = generate_carousel_images(slides, day_number)
        results["carousel"] = paths
        logger.info("[images] Generated %d carousel slides", len(paths))
    else:
        # Fallback: use ai_image_prompts if slides have no image_prompt
        prompts = content.get("ai_image_prompts") or {}
        carousel_prompt = (
            prompts.get("carousel_cover")
            or prompts.get("carousel")
            or "Purity Beans premium instant coffee jar, dark moody editorial"
        )
        from content_generator.creative.flux_generator import generate_image
        path = generate_image(carousel_prompt, width=1080, height=1080,
                              label=f"carousel_slide_1_day{day_number}", seed=day_number)
        if path:
            results["carousel"] = [path]
            logger.info("[images] Generated carousel cover from ai_image_prompts")

    # Reel thumbnail (reel_1)
    reel = content.get("reels", [{}])[0] if content.get("reels") else {}
    if reel:
        path = generate_reel_thumbnail(reel, day_number, label="reel_1")
        results["reel"] = path
        if path:
            logger.info("[images] Generated reel thumbnail: %s", path)

    return results


def _do_publish(content: dict, day_number: int) -> dict:
    """Post generated content to all configured social platforms."""
    from content_generator.publisher.dispatcher import publish_all
    return publish_all(content, day_number=day_number)


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
        result = run_now()
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
