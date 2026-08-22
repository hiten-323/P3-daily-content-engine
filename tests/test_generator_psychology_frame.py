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

    # Assert the contract, not a literal id. The defect being guarded is
    # _selected_frame_id doing str(list), which never matched a registry entry
    # and yielded "" — leaving generation ungoverned. Membership catches that
    # exactly, without making the publish gate hostage to the ORDER of
    # PSYCHOLOGY_FRAMES: this suite runs in CI before the evening publish, so a
    # content-registry reordering must not be able to stop a post going out.
    from content_generator.core.coffee_psychology import recommended_frame_for_format

    frame = result["psychology_frame"]
    assert frame, "no psychology frame selected — generation would be ungoverned"
    assert frame in recommended_frame_for_format("reel"), (
        f"selected frame {frame!r} is not a recommended frame for reels"
    )
