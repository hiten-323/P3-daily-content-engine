"""
Fallback safety.

The emergency templates publish unattended on the worst days — when every LLM
provider has failed and nobody is watching. They must therefore be the SAFEST
content in the repo. Historically they were the least reviewed: the fabricated
"40% chicory filler" statistic, the "first cup free" offer that never existed,
and the "Slide 1:" scaffolding that rendered into live carousel images were all
hardcoded here, not produced by the LLM.

Run: python tests/test_fallback_safety.py
"""
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LEARNING_DIR"] = tempfile.mkdtemp(prefix="pb_test_learning_")

failures = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def main():
    from content_generator.scheduler.fallback import (
        _EVERGREEN, _DISTRIBUTOR_TEMPLATES, emergency_content_set,
    )
    from content_generator.core.claim_verifier import verify_piece
    from content_generator.core.scroller_psychology import (
        payoff_strength, check_hook_decomposition,
    )
    from content_generator.core.content_contract import shareability
    from content_generator.core.brand_validator import validate_asset
    from content_generator.core.editorial_engine import get_valid_assets
    from content_generator.core.schema_validation import (
        ReelSchema, CarouselSchema, InstagramSchema, LinkedinSchema,
    )

    schemas = {"reel": ReelSchema, "carousel": CarouselSchema,
               "instagram_post": InstagramSchema, "linkedin_post": LinkedinSchema}
    templates = _EVERGREEN + _DISTRIBUTOR_TEMPLATES

    # 1. Not one unverifiable claim anywhere in the fallback set.
    print("\nNo unverified claims in any template:")
    for t in templates:
        found = verify_piece(t)
        check(f"{t['type']}: clean", not found,
              str([f"{f['type']}:{f['claim'][:40]}" for f in found]))

    # 2. The exact strings that reached the live grid must never return.
    print("\nThe specific historical incidents cannot recur:")
    blob = repr(templates).lower()
    for bad, what in (
        ("chicory filler", "the fabricated 40% chicory statistic"),
        ("first cup free", "the offer that never existed"),
        ("6,000 crore", "an unsourced market statistic"),
        ("34%", "an unsourced growth statistic"),
        ("india's first", "an unsubstantiated superlative"),
    ):
        check(f"absent: {what}", bad not in blob)
    check("no 'Slide N:' scaffolding in viewer copy",
          not re.search(r"slide\s*\d+\s*:", blob))

    # 3. Every template satisfies its schema — otherwise the publish gate drops
    #    it silently and the fallback is dead code.
    print("\nEvery template satisfies its schema:")
    for t in templates:
        try:
            schemas[t["type"]](**t)
            check(f"{t['type']}: schema", True)
        except Exception as e:
            check(f"{t['type']}: schema", False, str(e).splitlines()[1].strip()[:70])

    # 4. ...and every downstream quality gate.
    print("\nEvery template passes the quality gates:")
    for t in templates:
        check(f"{t['type']}: brand", validate_asset(t["type"], t)[0],
              str(validate_asset(t["type"], t)[1]))
        check(f"{t['type']}: payoff", payoff_strength(t)["passes"],
              payoff_strength(t)["reason"][:60])
        check(f"{t['type']}: shareability", shareability(t)["passes"],
              str(shareability(t)["score"]))
        check(f"{t['type']}: hook channels", check_hook_decomposition(t)["passes"])

    # 5. The assembled set must actually be publishable. A fallback that cannot
    #    clear its own gate means the engine goes silent on exactly the days it
    #    was built to cover — while still reporting success.
    print("\nThe assembled emergency set is publishable:")
    content = emergency_content_set(1)
    valid = get_valid_assets(content)
    check("emergency set yields valid assets", len(valid) >= 2, str(valid))
    check("includes an Instagram asset",
          any(v in valid for v in ("reel_1", "reel_2", "carousel", "instagram_post")),
          str(valid))

    print(f"\n{'FALLBACK UNSAFE' if failures else 'fallback safe'} "
          f"({len(failures)} failure(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
