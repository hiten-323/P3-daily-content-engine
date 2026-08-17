"""Regression tests for objective integrity and measurement truthfulness."""
from __future__ import annotations

from pathlib import Path

from config.api_versions import META_GRAPH_API_VERSION, SHOPIFY_API_VERSION
from content_generator.core.reward import coverage, explain, score


def test_current_api_versions_are_canonical() -> None:
    assert META_GRAPH_API_VERSION == "v24.0"
    assert SHOPIFY_API_VERSION == "2026-07"


def test_unknown_metric_is_not_a_zero() -> None:
    measured_zero = {"shares": 0}
    missing_shares = {}
    assert score(measured_zero, "followers") == 0.0
    assert score(missing_shares, "followers") == 0.0
    assert coverage(measured_zero, "followers") > coverage(missing_shares, "followers")
    detail = explain(missing_shares, "followers")
    assert "shares" in detail["missing_metrics"]
    assert "shares" not in detail["observed_metrics"]


def test_creation_kpi_is_available_for_learning_records() -> None:
    from content_generator.core.learning_engine import _entry_kpi

    assert _entry_kpi({"kpi": "followers"}) == "followers"
    assert _entry_kpi({"kpi": "revenue"}) == "revenue"
    assert _entry_kpi({}) is None


def test_unmeasured_records_cannot_become_teachable() -> None:
    from content_generator.core.learning_engine import _is_measurable

    assert not _is_measurable({"metrics": {}})
    assert not _is_measurable({"metrics": {"shares": 10}})
    assert _is_measurable({"metrics": {"shares": 10, "reach": 100}})


def test_no_legacy_meta_graph_v18_reference_in_python_sources() -> None:
    root = Path(__file__).resolve().parents[1]
    offenders = []
    for path in root.rglob("*.py"):
        if any(part in {".git", ".venv", "venv", "node_modules"} for part in path.parts):
            continue
        # The scan must not flag itself: this file necessarily contains the
        # very string it searches for, so it reported a permanent false
        # positive and failed on every run.
        if path.resolve() == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "v18.0" in text:
            offenders.append(str(path.relative_to(root)))
    assert offenders == [], f"Legacy Meta Graph API v18.0 references: {offenders}"
