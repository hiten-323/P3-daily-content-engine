"""Regression tests for creation-time KPI scoring in continuous learning."""

from content_generator.core import learning_engine


def test_historical_entry_uses_creation_kpi(monkeypatch):
    entry = {"kpi": "followers", "metrics": {"follows_gained": 100, "revenue": 0}}
    calls = []

    def fake_reward(metrics, kpi=None):
        calls.append(kpi)
        return 100.0 if kpi == "followers" else 1.0

    monkeypatch.setattr("content_generator.core.reward.score", fake_reward)
    monkeypatch.setattr(learning_engine, "_recency_factor", lambda _: 1.0)
    monkeypatch.setattr(learning_engine, "_objective_factor", lambda _: 1.0)

    assert learning_engine._weighted_score(entry) == 100.0
    assert calls == ["followers"]


def test_legacy_entry_remains_backward_compatible(monkeypatch):
    entry = {"metrics": {"follows_gained": 100}}
    calls = []

    def fake_reward(metrics, kpi=None):
        calls.append(kpi)
        return 7.0

    monkeypatch.setattr("content_generator.core.reward.score", fake_reward)
    monkeypatch.setattr(learning_engine, "_recency_factor", lambda _: 1.0)
    monkeypatch.setattr(learning_engine, "_objective_factor", lambda _: 1.0)

    assert learning_engine._weighted_score(entry) == 7.0
    assert calls == [None]
