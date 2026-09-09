from content_generator.rotation_safety import avoid_consecutive_tier


def test_allows_first_tier():
    assert avoid_consecutive_tier("occupation", None)


def test_rejects_same_tier():
    assert not avoid_consecutive_tier("occupation", "occupation")


def test_allows_different_tier_case_insensitive():
    assert avoid_consecutive_tier("Comparison", "occupation")
