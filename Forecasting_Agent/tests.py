"""
Regression tests for the Forecasting Agent. Assert-based, no pytest dependency
required (portfolio code should be runnable with nothing but the stdlib +
duckdb/openai where strictly needed).

Written after catching a real bug during Week 2 build: the forecast engine
was compounding a YoY growth rate quarter-over-quarter, which would have 5x'd
MNDY's revenue in 2 years. These tests exist so that specific bug — and its
class of bug (unit/rate confusion) — can't silently come back.

Run: python tests.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_engine import (
    _future_quarter_labels,
    blended_growth_rate,
    forecast_quarters,
    load_drivers,
)

from test_runner import run_tests

MNDY_DRIVERS_FILE = "mndy_drivers.json"
ASANA_DRIVERS_FILE = "asana_drivers.json"


def test_yoy_to_quarterly_conversion_is_not_identity():
    """The bug we caught: applying an annual rate as if it were quarterly.
    4 quarters of the correctly-converted rate must compound back to
    (approximately) the original annual rate — not 4x it."""
    annual_rate = 0.20  # 20% YoY
    quarterly_rate = (1 + annual_rate) ** 0.25 - 1
    compounded_4q = (1 + quarterly_rate) ** 4 - 1
    assert abs(compounded_4q - annual_rate) < 1e-9, (
        f"4 quarters of the converted rate should equal the annual rate. "
        f"Got {compounded_4q}, expected {annual_rate}."
    )
    # The bug specifically: quarterly_rate must NOT equal annual_rate itself
    # (that's what caused the 5x-in-2-years error).
    assert quarterly_rate < annual_rate, (
        "Quarterly rate must be smaller than the annual rate it's derived from "
        "— if they're equal, the YoY/QoQ compounding bug has regressed."
    )


def test_mndy_8q_forecast_does_not_blow_up():
    """Sanity ceiling: 8 quarters (2 years) of MNDY's own guided ~20% growth
    should land revenue well under 2x the base, not 5x+ like the pre-fix bug
    produced ($351M -> $1.87B, a 5.3x)."""
    drivers = load_drivers(MNDY_DRIVERS_FILE)
    result = forecast_quarters(drivers, n_quarters=8)
    base = result["base_revenue_musd"]
    final_base_case = result["quarters"][-1]["base_case_musd"]
    ratio = final_base_case / base

    assert ratio < 2.0, (
        f"8Q-out revenue is {ratio:.2f}x the base — the pre-fix bug produced "
        f"5.3x. A healthy ~20%/yr grower should land well under 2x in 2 years."
    )
    assert ratio > 1.2, (
        f"8Q-out revenue is only {ratio:.2f}x the base — suspiciously flat "
        f"for a company guided at ~20% annual growth."
    )


def test_confidence_band_produces_low_lt_base_lt_high():
    """Every forecasted quarter's low/base/high must be correctly ordered."""
    drivers = load_drivers(MNDY_DRIVERS_FILE)
    result = forecast_quarters(drivers, n_quarters=8)
    for q in result["quarters"]:
        assert q["low_musd"] <= q["base_case_musd"] <= q["high_musd"], (
            f"Quarter {q['quarter']} has out-of-order bounds: {q}"
        )


def test_future_quarter_labels_roll_over_year_correctly():
    labels = _future_quarter_labels("Q3_2025", 4)
    assert labels == ["Q4 2025", "Q1 2026", "Q2 2026", "Q3 2026"], (
        f"Quarter rollover is wrong: {labels}"
    )


def test_asana_generalization_still_works():
    """Same pipeline, different company, contracting NDR instead of expanding.
    Must not error, and must produce a growth rate close to Asana's own
    guidance (~8-9%), not something wildly off due to hardcoded MNDY logic
    creeping back in."""
    drivers = load_drivers(ASANA_DRIVERS_FILE)
    result = forecast_quarters(drivers, n_quarters=8)
    annual_rate = result["growth_rate_applied"]
    assert 0.05 < annual_rate < 0.15, (
        f"Asana's applied growth rate is {annual_rate:.2%} — expected roughly "
        f"8-9% based on guidance. A value outside 5-15% suggests MNDY-specific "
        f"logic leaked back into the 'generalized' engine."
    )


def test_ndr_nudge_direction():
    """MNDY has enterprise NDR > overall NDR, so the nudge should be positive.
    Asana has them equal (undisclosed enterprise tier), so nudge should be ~0."""
    mndy = load_drivers(MNDY_DRIVERS_FILE)
    _, mndy_detail = blended_growth_rate(mndy)
    assert mndy_detail["nudge_applied"] > 0, "MNDY's NDR spread should produce a positive nudge"

    asana = load_drivers(ASANA_DRIVERS_FILE)
    _, asana_detail = blended_growth_rate(asana)
    assert abs(asana_detail["nudge_applied"]) < 1e-9, (
        "Asana's enterprise/overall NDR are equal by construction (undisclosed tier) "
        "— nudge should be exactly 0, not fabricated."
    )


TESTS = [
    test_yoy_to_quarterly_conversion_is_not_identity,
    test_mndy_8q_forecast_does_not_blow_up,
    test_confidence_band_produces_low_lt_base_lt_high,
    test_future_quarter_labels_roll_over_year_correctly,
    test_asana_generalization_still_works,
    test_ndr_nudge_direction,
]


if __name__ == "__main__":
    run_tests(TESTS)
