"""Regression coverage for fail-closed Instagram token health."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOKEN_WORKFLOW = ROOT / ".github" / "workflows" / "instagram-token-health.yml"
DAILY_WORKFLOW = ROOT / ".github" / "workflows" / "daily.yml"


def test_missing_instagram_credentials_fail_closed() -> None:
    text = TOKEN_WORKFLOW.read_text(encoding="utf-8")
    marker = "if not account_id or not token:"
    assert marker in text
    block = text.split(marker, 1)[1].split("query =", 1)[0]
    assert "sys.exit(1)" in block
    assert "sys.exit(0)" not in block


def test_token_health_uses_graph_v24() -> None:
    text = TOKEN_WORKFLOW.read_text(encoding="utf-8")
    assert "https://graph.facebook.com/v24.0/" in text


def test_extended_content_is_explicit_in_daily_workflow() -> None:
    text = DAILY_WORKFLOW.read_text(encoding="utf-8")
    assert "ENABLE_EXTENDED_CONTENT:" in text
