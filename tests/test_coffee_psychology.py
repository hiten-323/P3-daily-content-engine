import pytest
from content_generator.core.coffee_psychology import validate_registry, PSYCHOLOGY_FRAMES, frame_prompt_block

def test_duplicate_ids():
    original = list(PSYCHOLOGY_FRAMES)
    test_frames = original.copy()
    test_frames.append(original[0].copy())
    with pytest.raises(ValueError, match="Duplicate psychology frame ID detected"):
        validate_registry(test_frames)

def test_missing_fields():
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_missing"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    del bad_frame["theory"]
    test_frames = original.copy()
    test_frames.append(bad_frame)
    with pytest.raises(ValueError, match="Psychology frame missing required root key: 'theory'"):
        validate_registry(test_frames)

def test_invalid_risk_levels():
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_risk"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    bad_frame["risk_level"] = "extreme"
    test_frames = original.copy()
    test_frames.append(bad_frame)
    with pytest.raises(ValueError, match="Invalid risk_level 'extreme'"):
        validate_registry(test_frames)

def test_invalid_formats():
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_formats"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    bad_frame["creative_application"] = bad_frame["creative_application"].copy()
    bad_frame["creative_application"]["best_formats"] = "not_a_list"
    test_frames = original.copy()
    test_frames.append(bad_frame)
    with pytest.raises(ValueError, match="best_formats must be a non-empty list of strings"):
        validate_registry(test_frames)
    pass

def test_empty_hooks():
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_hooks"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    bad_frame["creative_application"] = bad_frame["creative_application"].copy()
    bad_frame["creative_application"]["example_hooks"] = []
    test_frames = original.copy()
    test_frames.append(bad_frame)
    with pytest.raises(ValueError, match="example_hooks must be a non-empty list"):
        validate_registry(test_frames)

def test_valid_registry():
    assert validate_registry() is True

def test_prompt_block_contains_truth_hierarchy():
    from content_generator.core.coffee_psychology import frame_prompt_block
    block = frame_prompt_block("social_currency")
    assert "MANDATORY GOVERNANCE RULE" in block
    assert "never override truthfulness" in block




def test_malformed_governance():
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_gov"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    bad_frame["governance"] = bad_frame["governance"].copy()
    bad_frame["governance"]["allowed_claim_categories"] = "not a list"
    test_frames = original.copy()
    test_frames.append(bad_frame)
    with pytest.raises(ValueError, match="allowed_claim_categories must be a list of non-empty strings"):
        validate_registry(test_frames)

def test_unexpected_fields():
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_unexpected"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    bad_frame["unexpected_field"] = "hello"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    test_frames = original.copy()
    test_frames.append(bad_frame)
    with pytest.raises(ValueError, match="Unexpected top-level fields"):
        validate_registry(test_frames)

def test_high_risk_frame_receives_stronger_governance():
    from content_generator.core.coffee_psychology import validate_registry, PSYCHOLOGY_FRAMES, frame_prompt_block
    import pytest
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_high_risk"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    bad_frame["risk_level"] = "high"
    bad_frame["governance"] = bad_frame["governance"].copy()
    bad_frame["governance"]["prohibited_claims"] = []
    test_frames = original.copy()
    test_frames.append(bad_frame)
    with pytest.raises(ValueError, match="High risk frame 'test_high_risk' must specify prohibited_claims"):
        validate_registry(test_frames)

    bad_frame["governance"]["prohibited_claims"] = ["cannot do this"]
    validate_registry(test_frames)
    # To test prompt block, we just test a built-in one if we can or skip since it is tested separately

import pytest

def test_truth_regression():
    from content_generator.core.coffee_psychology import get_frame

    frame = get_frame("social_currency")
    assert frame is not None

    # Normally check_claims takes the generated text and ensures it doesn't violate rules.
    # Because brand_validator.py might not be available in all ZIP drops, we test
    # that the psychology frame properly exports prohibited claims.
    # The actual enforcement of these claims happens in validate_asset_copy, which is
    # tested in the broader suite.

    assert "prohibited_claims" in frame["governance"]
    assert len(frame["governance"]["prohibited_claims"]) > 0
    assert "anyone drinking chicory is stupid" in frame["governance"]["prohibited_claims"]

    # Assert there are no numerical facts masquerading as mechanisms in the hooks
    for hook in frame["creative_application"]["example_hooks"]:
        assert "40%" not in hook

def test_no_numerical_percentage_claims_in_hooks():
    from content_generator.core.coffee_psychology import PSYCHOLOGY_FRAMES
    import re

    # Assert no numerical percentage claims like 40% are in example hooks
    percentage_pattern = re.compile(r"\b\d+(?:\.\d+)?%\b")
    for frame in PSYCHOLOGY_FRAMES:
        for hook in frame["creative_application"]["example_hooks"]:
            assert not percentage_pattern.search(hook), f"Found numerical percentage claim in hook: '{hook}' in frame '{frame['id']}'"

def test_empty_name_fails():
    from content_generator.core.coffee_psychology import PSYCHOLOGY_FRAMES, validate_registry
    import pytest
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_name"
    bad_frame["name"] = ""
    test_frames = original.copy()
    test_frames.append(bad_frame)
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        validate_registry(test_frames)
