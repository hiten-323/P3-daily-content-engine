"""
Scroller psychology — ADR-002 Phases 1-3.

Phase 1 records the decision dimensions, Phase 2 rejects hooks with no payoff,
Phase 3 rejects video whose three hook channels repeat each other.
Run: python tests/test_scroller_psychology.py
"""
import os
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
    from content_generator.core.scroller_psychology import (
        MECHANISMS, MECHANISMS_BY_ID, STATES_BY_ID, describe,
        classify_mechanism, classify_state, payoff_strength,
        check_hook_decomposition,
    )
    from content_generator.core.learning_engine import record_performance, _load_log

    bait = {"hook": "Most people do not know this about their coffee",
            "caption": "You will be shocked."}
    teaching = {"hook": "Your coffee turns bitter in 2 minutes",
                "caption": "That is chicory. Check the label on the back — read the "
                           "ingredient list next time you buy."}

    # ── Phase 1: dimensions are recorded, never invented ──────────────────
    print("\nPhase 1 — decision dimensions:")
    check("registry is non-empty", len(MECHANISMS) >= 10, str(len(MECHANISMS)))
    check("every mechanism states a payoff requirement",
          all(m.get("payoff_requirement") for m in MECHANISMS))
    check("no 'default' mechanism exists", "default" not in MECHANISMS_BY_ID)
    check("classified mechanism is a real id",
          classify_mechanism(teaching) in MECHANISMS_BY_ID)
    check("classified state is a real id",
          classify_state(teaching) in STATES_BY_ID)
    # Unknown must stay unknown rather than becoming a placeholder.
    check("empty copy -> None mechanism, not a guess", classify_mechanism({}) is None)
    check("empty copy -> None state, not a guess", classify_state({}) is None)

    dims = describe(teaching)
    for field in ("scroller_state", "attention_mechanism", "psychology_frame",
                  "hook_strategy", "payoff_type", "hook_promise",
                  "payoff_present", "payoff_validation_status",
                  "platform", "format", "funnel_stage",
                  "business_objective", "target_kpi_at_creation",
                  "decision_version"):
        check(f"describe() emits {field}", field in dims)
    check("describe states its basis", "Phase 4" in dims.get("basis", ""))

    # The dimensions must survive into the learning log, or mechanism-level
    # learning is impossible no matter how good the classifier is.
    print("\nPhase 1 — dimensions reach the learning record:")
    entry = record_performance(
        asset_id="test_asset", track="brand", hook="h",
        metrics={"reach": 10},
        attention_mechanism="curiosity_gap", scroller_state="curious",
        psychology_frame="revelation")
    check("attention_mechanism persisted", entry.get("attention_mechanism") == "curiosity_gap")
    check("scroller_state persisted", entry.get("scroller_state") == "curious")
    check("psychology_frame persisted", entry.get("psychology_frame") == "revelation")
    check("record is on disk", any(e.get("asset_id") == "test_asset" for e in _load_log()))

    # ── Phase 2: payoff ───────────────────────────────────────────────────
    print("\nPhase 2 — payoff gate:")
    b = payoff_strength(bait)
    check("bait rejected", b["passes"] is False, b["reason"])
    check("bait detected as an open loop", b["opens_loop"] is True)
    check("rejection explains why", "learns nothing" in b["reason"] or "bait" in b["reason"])
    g = payoff_strength(teaching)
    check("teaching content passes", g["passes"] is True, g["reason"])
    check("payoff kinds named", len(g["kinds"]) >= 1, str(g["kinds"]))
    check("no copy -> fails", payoff_strength({})["passes"] is False)

    # Content that never opened a loop is not punished for having no reveal,
    # but must still deliver something.
    demo = {"hook": "Watch what happens", "caption": "Side by side: our jar versus "
                                                     "a chicory blend. See the difference."}
    check("demonstration content passes on its own terms",
          payoff_strength(demo)["passes"] is True, payoff_strength(demo)["reason"])

    # ── Phase 3: hook decomposition ───────────────────────────────────────
    print("\nPhase 3 — hook channels are distinct:")
    dup = {"hook_text": "READ THE LABEL", "hook_spoken": "Read the label"}
    dis = {"hook_text": "READ THE LABEL",
           "hook_spoken": "One line here most people skip",
           "hook_visual_concept": "extreme close up of the ingredient panel"}
    check("identical on-screen and spoken rejected",
          check_hook_decomposition(dup)["passes"] is False)
    check("distinct channels pass", check_hook_decomposition(dis)["passes"] is True)
    check("single channel is not penalised",
          check_hook_decomposition({"hook_text": "READ THE LABEL"})["passes"] is True)

    # ── The gates are wired into the ONE canonical chain ──────────────────
    print("\nGates are enforced through the canonical chain:")
    from content_generator.core import editorial_engine as ee
    real = ee.get_valid_assets
    try:
        ee.get_valid_assets = lambda c: ["reel_1"]
        # Bait reel: strong hook, no payoff -> must not survive.
        kept = ee._apply_growth_director_gates(
            {"reels": [dict(bait, type="reel")]}, ["reel_1"])
        check("bait reel dropped by the gate chain", kept == [], str(kept))
        # Teaching reel with distinct hooks -> survives.
        good_reel = dict(teaching, type="reel",
                         hook_text="READ THE LABEL",
                         hook_spoken="One line here most people skip")
        kept = ee._apply_growth_director_gates({"reels": [good_reel]}, ["reel_1"])
        check("teaching reel survives the gate chain", kept == ["reel_1"], str(kept))
    finally:
        ee.get_valid_assets = real

    # ── Contract: unavailable data is null, never invented ────────────────
    print("\nMissing decision data is not fabricated:")
    empty = describe({}, {})
    for f in ("attention_mechanism", "scroller_state", "psychology_frame",
              "hook_strategy", "payoff_type", "platform", "format",
              "funnel_stage", "business_objective", "target_kpi_at_creation"):
        check(f"{f} is None when unavailable", empty.get(f) is None, repr(empty.get(f)))
    check("no field is the string 'default'",
          "default" not in [str(v).lower() for v in empty.values()])
    # An undetermined boolean must be None, not False: False is a finding.
    for f in ("payoff_present", "hook_layers_distinct"):
        check(f"{f} is None when undetermined, not False",
              empty.get(f) is None, repr(empty.get(f)))
    check("no unknown is coerced to 0 or False",
          not any(v == 0 or v is False for v in empty.values()))
    check("decision_version always stamped", bool(empty.get("decision_version")))
    check("payoff_gate_version stamped", bool(payoff_strength({})["payoff_gate_version"]))

    # ── Contract: target KPI preserved from creation time ─────────────────
    print("\nTarget KPI is preserved from creation time:")
    from content_generator.core.reward import get_active_kpi
    rec = describe({}, {"target_kpi_at_creation": "followers"})
    check("KPI read from the content record", rec["target_kpi_at_creation"] == "followers")
    e = record_performance(asset_id="kpi_test", track="brand",
                           metrics={"reach": 5}, kpi_at_creation="followers")
    check("KPI stamped on the learning record", e.get("kpi") == "followers")
    check("get_active_kpi still resolves", bool(get_active_kpi()))

    # ── Contract: Phase 1 is OBSERVATIONAL — no behaviour change ──────────
    print("\nPhase 1 is observational only:")
    import inspect
    from content_generator.core import scroller_psychology as sp
    src = inspect.getsource(sp)
    for forbidden, why in (
        ("WEIGHT_PROFILES", "must not touch the reward function"),
        ("def score(",      "must not define a second reward"),
        ("def approved_assets", "must not define a second publish gate"),
    ):
        check(f"scroller layer {why}", forbidden not in src)
    # It must not select frames — Phase 4 is not active.
    check("no mechanism selection is active",
          not any(n.startswith("select_") for n in dir(sp)), str(dir(sp))[:60])

    # ── Contract: existing behaviour unchanged except payoff rejection ────
    print("\nExisting subsystems unchanged:")
    from content_generator.core.reward import score as reward_score
    check("reward returns a scalar", isinstance(reward_score({"follows_gained": 1}), float))
    check("reward still ranks audience over Rs 1",
          reward_score({"follows_gained": 10000}) > reward_score({"revenue": 1.0}))
    from content_generator.core.editorial_engine import (
        approved_assets, resolve_psychology_governance, EditorialRejectException,
    )
    check("canonical gate still exported", callable(approved_assets))
    try:
        resolve_psychology_governance({"psychology_frame": "default"})
        check("psychology governance still fails closed", False, "did not raise")
    except EditorialRejectException:
        check("psychology governance still fails closed", True)
    from content_generator.core.claim_verifier import verify_claims
    check("fact verification still active",
          len(verify_claims("Most big brands add 50 percent chicory.")) > 0)
    from content_generator.core.content_balance import MAX_PRODUCT_SHARE
    check("content balance still 20%", abs(MAX_PRODUCT_SHARE - 0.20) < 1e-9)

    print(f"\n{'SCROLLER LAYER BROKEN' if failures else 'scroller psychology enforced'} "
          f"({len(failures)} failure(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
