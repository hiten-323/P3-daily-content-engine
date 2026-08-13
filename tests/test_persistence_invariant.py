"""
Git persistence invariant — learning and daily content must be recoverable
from the repository without the Actions cache.

If the cache key evaporates, the next run must still find:
  - output/learning/*.json  (force-added every run)
  - output/content_YYYY-MM-DD.json (force-added every generate)

This test is structural: it asserts the workflow and generator contracts that
make that reconstruction possible. It does not invent metrics.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "daily.yml"
GENERATOR = ROOT / "content_generator" / "pipeline" / "generator.py"


def main() -> None:
    wf = WORKFLOW.read_text(encoding="utf-8")
    gen = GENERATOR.read_text(encoding="utf-8")

    # Persist step force-adds the paths that matter.
    assert "git add -f output/learning/" in wf, "learning must be force-added to Git"
    assert re.search(r'git add -f ["\']?output/content_', wf), "daily content JSON must be force-added"

    # Push failure is fatal — publish slots cannot load unpushed content.
    assert "Could not push run artefacts" in wf or "publish slots cannot load" in wf

    # Generator writes content_{date}.json under output/ — the same path the
    # workflow force-adds and the morning/evening slots load.
    assert 'content_{date_str}.json' in gen or 'f"content_{date_str}.json"' in gen

    # Extended content is resolved via policy helper, not a bare env default.
    assert "_extended_content_enabled" in gen
    assert "enable_extended_content" in gen

    print("persistence invariant: PASS")


if __name__ == "__main__":
    main()
