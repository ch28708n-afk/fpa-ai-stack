"""Regression tests for the Live Artifacts Demo's deterministic logic.

commentary.py's network call is mocked, never hitting real OpenRouter.
Run: python tests.py
"""

from unittest.mock import MagicMock, patch

import commentary
import tools

CURRENT_PERIOD = "current"
NEXT_PERIOD = "next_period (simulated refresh)"
RIVERBEND = "Riverbend Assembly"
COLDWATER = "Coldwater Stamping"


def test_executive_pulse_math_ties_out():
    pulse = tools.get_executive_pulse(CURRENT_PERIOD)
    assert pulse["revenue_variance"] == pulse["revenue_actual"] - pulse["revenue_budget"]
    assert pulse["revenue_variance"] == 14_500_000
    assert pulse["revenue_variance_pct"] == 3.6
    assert pulse["margin_variance_pts"] == -1.7
    assert pulse["unit_variance"] == 2700


def test_variance_bridge_revenue_drivers_sum_to_variance():
    bridge = tools.get_variance_bridge(CURRENT_PERIOD)
    driver_sum = sum(bridge["revenue_drivers"].values())
    assert driver_sum == bridge["revenue_actual"] - bridge["revenue_budget"], (
        "price + volume + mix must reconcile exactly to the revenue variance"
    )
    assert bridge["largest_revenue_driver"] == "volume"


def test_variance_bridge_cost_drivers_sum_to_variance():
    bridge = tools.get_variance_bridge(CURRENT_PERIOD)
    driver_sum = sum(bridge["cost_drivers"].values())
    assert driver_sum == bridge["cost_actual"] - bridge["cost_budget"], (
        "material + labor + freight must reconcile exactly to the cost variance"
    )
    assert bridge["largest_cost_driver"] == "material"


def test_manufacturing_flags_riverbend_in_current_period():
    mfg = tools.get_manufacturing_signals(CURRENT_PERIOD)
    assert mfg["flagged_plants"] == [RIVERBEND]


def test_manufacturing_flags_flip_to_coldwater_next_period():
    """The whole point of the refresh demo: swapping the data source must
    change which plant gets flagged, proving the logic isn't hardcoded to
    one company's specific numbers."""
    mfg = tools.get_manufacturing_signals(NEXT_PERIOD)
    assert mfg["flagged_plants"] == [COLDWATER]
    assert RIVERBEND not in mfg["flagged_plants"], (
        "Riverbend's defect rate and lead time both improved next period — it must NOT still be flagged"
    )


def test_flagging_threshold_boundaries():
    """Exactly at the 0.3pt threshold must NOT flag (strictly-greater-than
    semantics); just over it must flag. Guards against an off-by-one on the
    comparison operator."""

    def fake_load(defect_delta):
        def _loader(source=CURRENT_PERIOD):
            return {
                "manufacturing": {
                    "plants": [
                        {
                            "name": "Boundary Plant",
                            "units_produced": 1000,
                            "defect_rate_pct": round(1.0 + defect_delta, 2),
                            "defect_rate_pct_prior": 1.0,
                            "supplier_lead_time_days": 10,
                            "supplier_lead_time_days_prior": 10,
                        }
                    ]
                }
            }

        return _loader

    original_load = tools._load
    try:
        tools._load = fake_load(0.30)
        assert tools.get_manufacturing_signals()["flagged_plants"] == [], "exactly 0.3pt must not flag"

        tools._load = fake_load(0.31)
        assert tools.get_manufacturing_signals()["flagged_plants"] == ["Boundary Plant"], "0.31pt must flag"
    finally:
        tools._load = original_load


def test_snapshot_includes_all_three_layers():
    snap = tools.get_snapshot(CURRENT_PERIOD)
    assert set(snap.keys()) >= {"company", "period", "as_of", "executive_pulse", "variance_bridge", "manufacturing"}


def test_commentary_connects_flagged_plant_into_prompt():
    fake_response = MagicMock()
    fake_response.json.return_value = {"choices": [{"message": {"content": "Riverbend drove the cost overrun."}}]}
    snapshot = tools.get_snapshot(CURRENT_PERIOD)
    with patch("commentary.requests.post", return_value=fake_response) as mock_post:
        result = commentary.generate_commentary(snapshot)
    assert result == "Riverbend drove the cost overrun."
    sent_body = mock_post.call_args.kwargs["json"]
    prompt = sent_body["messages"][1]["content"]
    assert RIVERBEND in prompt, "the flagged plant must reach the prompt for the LLM to connect it"
    assert "material" in prompt, "the largest cost driver must reach the prompt"


def test_commentary_propagates_http_errors():
    fake_response = MagicMock()
    fake_response.raise_for_status.side_effect = Exception("timeout")
    with patch("commentary.requests.post", return_value=fake_response):
        try:
            commentary.generate_commentary(tools.get_snapshot(CURRENT_PERIOD))
            raise AssertionError("expected the upstream exception to propagate")
        except Exception as e:
            assert "timeout" in str(e), "the dashboard's try/except relies on this propagating, not being swallowed"


def _run_all_tests():
    tests = [(name, fn) for name, fn in list(globals().items()) if name.startswith("test_") and callable(fn)]
    results = []
    for name, fn in tests:
        try:
            fn()
            results.append((name, True, None))
        except Exception as e:
            results.append((name, False, str(e)))
    return results


if __name__ == "__main__":
    import sys

    outcomes = _run_all_tests()
    for name, ok, error in outcomes:
        status = "PASS" if ok else f"FAIL: {error}"
        sys.stdout.write(f"{status} {name}\n")
    passed = sum(1 for _, ok, _ in outcomes if ok)
    sys.stdout.write(f"\n{passed}/{len(outcomes)} passed\n")
    if passed != len(outcomes):
        sys.exit(1)
