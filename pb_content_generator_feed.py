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
"""
from __future__ import annotations
import datetime
import json
import logging
import os

logger = logging.getLogger(__name__)

_OUTPUT_DIR = os.getenv("PB_OUTPUT_DIR", "output")


def _todays_path() -> str:
    date_str = datetime.date.today().isoformat()
    return os.path.join(_OUTPUT_DIR, f"content_{date_str}.json")


def get_todays_content(
    force_generate: bool = False,
    day_number: int | None = None,
) -> dict:
    """Return today's content dict — cached from disk if available, else generate."""
    path = _todays_path()

    if not force_generate and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
            logger.info("[feed] Loaded today's content from %s", path)
            return content
        except Exception as e:
            logger.warning("[feed] Could not read %s (%s) — regenerating", path, e)

    # Generate fresh (requires at least one LLM provider key)
    from content_generator import configure
    from content_generator.pipeline.generator import generate_daily_content, save_content

    configure(load_env=True, setup_logging=False)
    content = generate_daily_content(day_number=day_number)
    try:
        save_content(content, output_dir=_OUTPUT_DIR)
    except Exception as e:
        logger.warning("[feed] Generated content but could not save: %s", e)
    return content


if __name__ == "__main__":
    c = get_todays_content()
    keys = ", ".join(k for k in c.keys() if not k.startswith("_"))
    print(f"Loaded content for day {c.get('day_number')} ({c.get('date')})")
    print(f"Sections: {keys}")
