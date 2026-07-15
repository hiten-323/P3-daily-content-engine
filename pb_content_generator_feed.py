"""
pb_content_generator_feed — simple public accessor for the day's content.

    from pb_content_generator_feed import get_todays_content
    content = get_todays_content()

get_todays_content() returns today's content dict:
  1. If output/content_<today>.json already exists (produced by the daily
     pipeline), it is loaded from disk — FREE, no LLM calls.
  2. Otherwise it is generated fresh (needs LLM API keys) and saved, so the
     next call is cached.

Pass force_generate=True to always regenerate. Pass day_number to override
the auto day counter (testing).

Decision-layer extensions (Founder OS):
    content = get_todays_content(include_recommendations=True)
    # -> {"content": {...}, "recommendation": {...}, "experiment": {...},
    #     "campaign": "...", "playbook": "..."}

    content = get_todays_content(include_metadata=True)
    # -> content dict with content["_asset_metadata"] = per-asset records

This turns get_todays_content() from a content function into a DECISION
function: every asset carries expected business impact, an experiment, a
campaign, and a playbook — the feedback path the learning loop compounds on.
"""
from __future__ import annotations
import datetime
import json
import logging
import os

logger = logging.getLogger(__name__)


def _output_dir() -> str:
    # Read dynamically so PB_OUTPUT_DIR set after import still takes effect.
    return os.getenv("PB_OUTPUT_DIR", "output")


def _todays_path() -> str:
    date_str = datetime.date.today().isoformat()
    return os.path.join(_output_dir(), f"content_{date_str}.json")


def get_todays_content(
    force_generate: bool = False,
    day_number: int | None = None,
    include_metadata: bool = False,
    include_recommendations: bool = False,
) -> dict:
    """
    Return today's content — cached from disk if available, else generate.

    include_metadata:        attach content["_asset_metadata"] (per-asset
                             Company Memory records: content_id, hook, cta,
                             campaign, experiment, playbook, status).
    include_recommendations: return the DECISION bundle instead of a bare dict:
                             {"content", "recommendation", "experiment",
                              "campaign", "playbook"}.
    """
    path = _todays_path()

    content = None
    if not force_generate and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
            logger.info("[feed] Loaded today's content from %s", path)
        except Exception as e:
            logger.warning("[feed] Could not read %s (%s) — regenerating", path, e)

    if content is None:
        # Generate fresh (requires at least one LLM provider key)
        from content_generator import configure
        from content_generator.pipeline.generator import generate_daily_content, save_content

        configure(load_env=True, setup_logging=False)
        content = generate_daily_content(day_number=day_number)
        try:
            save_content(content, output_dir=_output_dir())
        except Exception as e:
            logger.warning("[feed] Generated content but could not save: %s", e)

    day = content.get("day_number", day_number or 0)

    if include_metadata or include_recommendations:
        try:
            from content_generator.intelligence.decision_layer import attach_asset_metadata
            attach_asset_metadata(content, day)
        except Exception as e:
            logger.warning("[feed] metadata attach failed: %s", e)

    if include_recommendations:
        try:
            from content_generator.intelligence.decision_layer import plan_today
            plan = plan_today(day)
            return {"content": content, **plan}
        except Exception as e:
            logger.warning("[feed] recommendations failed: %s", e)
            return {"content": content, "recommendation": {}, "experiment": {},
                    "campaign": "", "playbook": "Baseline_v1"}

    return content


if __name__ == "__main__":
    c = get_todays_content()
    keys = ", ".join(k for k in c.keys() if not k.startswith("_"))
    print(f"Loaded content for day {c.get('day_number')} ({c.get('date')})")
    print(f"Sections: {keys}")
