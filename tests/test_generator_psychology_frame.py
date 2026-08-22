"""Regression coverage for generator psychology frame selection."""

from content_generator.pipeline import generator


def test_generator_uses_first_valid_recommended_psychology_frame(monkeypatch):
    monkeypatch.setenv("ENABLE_USAGE_LOG", "false")
    monkeypatch.setattr(generator, "_extended_content_enabled", lambda: False)

    def fake_llm_call(prompt: str, label: str, max_tokens: int = 3000) -> dict:
        if label == "video_prompts":
            return {"video_prompts": {}}
        return {"id": label}

    monkeypatch.setattr(generator, "llm_call", fake_llm_call)

    result = generator.generate_daily_content(day_number=0, research_context={})

    assert result["psychology_frame"] == "revelation"
