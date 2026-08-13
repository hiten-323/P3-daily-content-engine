from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "daily.yml"


def main() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    # Canonical production windows.
    assert "cron: '30 0 * * *'" in text
    assert "cron: '30 4 * * *'" in text
    assert "cron: '30 16 * * *'" in text

    # Manual execution must select a slot instead of inferring it from wall time.
    assert "Manual slot to execute — never infer from wall-clock time" in text
    assert "required: true" in text
    assert "- generate" in text and "- morning" in text and "- evening" in text

    # Generate is not a publication slot.
    assert "no publication expected at 06:00 IST" in text
    assert "GENERATE verified" in text

    # Publishing slots have an actual Meta preflight, before the pipeline runs.
    assert "Verify Meta publishing access" in text
    assert "graph.facebook.com/v24.0/" in text
    assert "env.FORCE_SLOT != 'generate'" in text

    # Repository synchronization failures must never be swallowed.
    assert "git pull --rebase --autostash || true" not in text
    assert re.search(r"git pull --rebase --autostash\s*$", text, re.M)

    # No stale production-window references.
    assert "08:00 / 20:00" not in text
    assert "08:00/20:00" not in text

    print("workflow contract: PASS")


if __name__ == "__main__":
    main()
