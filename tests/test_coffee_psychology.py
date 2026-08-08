import pytest
from content_generator.core.coffee_psychology import validate_registry, PSYCHOLOGY_FRAMES, frame_prompt_block

def test_duplicate_ids():
    original = list(PSYCHOLOGY_FRAMES)
    PSYCHOLOGY_FRAMES.append(original[0].copy())
    with pytest.raises(ValueError, match="Duplicate psychology frame ID detected"):
        validate_registry()
    PSYCHOLOGY_FRAMES.clear()
    PSYCHOLOGY_FRAMES.extend(original)

def test_missing_fields():
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_missing"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    del bad_frame["theory"]
    PSYCHOLOGY_FRAMES.append(bad_frame)
    with pytest.raises(ValueError, match="Psychology frame missing required root key: 'theory'"):
        validate_registry()
    PSYCHOLOGY_FRAMES.clear()
    PSYCHOLOGY_FRAMES.extend(original)

def test_invalid_risk_levels():
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_risk"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    bad_frame["risk_level"] = "extreme"
    PSYCHOLOGY_FRAMES.append(bad_frame)
    with pytest.raises(ValueError, match="Invalid risk_level 'extreme'"):
        validate_registry()
    PSYCHOLOGY_FRAMES.clear()
    PSYCHOLOGY_FRAMES.extend(original)

def test_invalid_formats():
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_formats"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    bad_frame["creative_application"] = bad_frame["creative_application"].copy()
    bad_frame["creative_application"]["best_formats"] = "not_a_list"
    PSYCHOLOGY_FRAMES.append(bad_frame)
    with pytest.raises(ValueError, match="best_formats must be a non-empty list of strings"):
        validate_registry()
    PSYCHOLOGY_FRAMES.pop()
    pass

def test_empty_hooks():
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_hooks"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    bad_frame["creative_application"] = bad_frame["creative_application"].copy()
    bad_frame["creative_application"]["example_hooks"] = []
    PSYCHOLOGY_FRAMES.append(bad_frame)
    with pytest.raises(ValueError, match="example_hooks must be a non-empty list"):
        validate_registry()
    PSYCHOLOGY_FRAMES.pop()

def test_valid_registry():
    assert validate_registry() is True

def test_prompt_block_contains_truth_hierarchy():
    block = frame_prompt_block()
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
    PSYCHOLOGY_FRAMES.append(bad_frame)
    with pytest.raises(ValueError, match="allowed_claim_categories must be a list of non-empty strings"):
        validate_registry()
    PSYCHOLOGY_FRAMES.clear()
    PSYCHOLOGY_FRAMES.extend(original)

def test_unexpected_fields():
    original = list(PSYCHOLOGY_FRAMES)
    bad_frame = original[0].copy()
    bad_frame["id"] = "test_unexpected"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    bad_frame["unexpected_field"] = "hello"
    bad_frame["version"] = 1
    bad_frame["objective"] = "trust"
    PSYCHOLOGY_FRAMES.append(bad_frame)
    with pytest.raises(ValueError, match="Unexpected top-level fields"):
        validate_registry()
    PSYCHOLOGY_FRAMES.clear()
    PSYCHOLOGY_FRAMES.extend(original)

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

    PSYCHOLOGY_FRAMES.append(bad_frame)
    with pytest.raises(ValueError, match="High risk frame 'test_high_risk' must specify prohibited_claims"):
        validate_registry()

    bad_frame["governance"]["prohibited_claims"] = ["cannot do this"]
    validate_registry() # Should pass now

    # Check that high risk warning is in prompt block
    prompt = frame_prompt_block()
    assert "WARNING (HIGH RISK FRAME)" in prompt

    PSYCHOLOGY_FRAMES.clear()
    PSYCHOLOGY_FRAMES.extend(original)

import pytest

def test_truth_regression():
    from content_generator.core.brand_validator import validate_asset_copy
    from content_generator.core.coffee_psychology import get_frame

    frame = get_frame("social_currency")
    assert frame is not None

    # Normally check_claims takes the generated text and ensures it doesn't violate rules
    # In the actual implementation, where do we validate claims?

    valid_text = "purity beans is a 100% coffee brand. We don't use chicory. visit p3online.in for more info."
    is_valid, _ = validate_asset_copy(valid_text, check_brand_facts=True, check_website=True, check_brand_mention=True, check_length=False)
    assert is_valid

    # Fabricated claim that is prohibited - weight loss
    invalid_text = "purity beans is a 100% coffee brand. 40% of coffee contains chicory, which causes weight loss. visit p3online.in"
    is_valid, _ = validate_asset_copy(invalid_text, check_brand_facts=True, check_website=True, check_brand_mention=True, check_length=False)
    assert not is_valid

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
    PSYCHOLOGY_FRAMES.append(bad_frame)
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        validate_registry()
    PSYCHOLOGY_FRAMES.clear()
    PSYCHOLOGY_FRAMES.extend(original)
