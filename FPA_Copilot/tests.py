"""
Regression tests for FPA_Copilot's deterministic tools (tools.py). No LLM
involved — these test the Python logic the orchestrator calls into, which is
where all the actual financial judgment lives.

Run: python tests.py
"""
from tools import get_forecast, get_variance_commentary, get_reconciliation_check


def test_ambiguous_company_match_errors_instead_of_blending():
    """Regression test for a real bug caught during the Phase 3 scrub: a
    broad substring query matching multiple companies used to silently blend
    both companies' quarters into one result, reporting only the first
    company's name. Now it must return a disambiguation error."""
    result = get_forecast("a")  # matches both "Asana..." and "monday.com..."
    assert "error" in result, f"Ambiguous query should error, got: {result}"
    assert "multiple companies" in result["error"]


def test_specific_company_queries_still_resolve():
    mndy = get_forecast("MNDY")
    assert mndy["company"] == "monday.com (MNDY)"
    assert len(mndy["forecast_quarters"]) == 8

    asana = get_forecast("Asana")
    assert asana["company"] == "Asana, Inc. (ASAN)"


def test_variance_commentary_blocks_on_unconfirmed_material_variance():
    result = get_variance_commentary([
        {"name": "Revenue", "actual": 1240000, "budget": 1180000, "known_reason": "new client wins"},
        {"name": "Direct Costs", "actual": 496000, "budget": 448400},  # no known_reason
    ])
    assert result["sign_off_status"].startswith("BLOCKED")
    assert len(result["open_items"]) == 1
    assert result["open_items"][0]["name"] == "Direct Costs"


def test_variance_commentary_clears_when_all_confirmed():
    result = get_variance_commentary([
        {"name": "Revenue", "actual": 1240000, "budget": 1180000, "known_reason": "new client wins"},
    ])
    assert result["sign_off_status"] == "CLEAR"


def test_reconciliation_blocks_on_duplicate_even_when_math_ties():
    """The core judgment from the Month-End Close Toolkit's Example 2: a rec
    that mathematically ties can still be BLOCKED by a high-risk item."""
    result = get_reconciliation_check(
        net_diff_usd=11800, explained_usd=11800,
        items=[{"description": "Vendor invoice posted twice", "amount": 11500, "category": "duplicate"}],
    )
    assert result["mathematically_ties"] is True
    assert result["sign_off_status"].startswith("BLOCKED")
    assert len(result["blockers"]) == 1


def test_reconciliation_clears_when_no_blockers_and_ties():
    result = get_reconciliation_check(
        net_diff_usd=5000, explained_usd=5000,
        items=[{"description": "Timing difference", "amount": 5000, "category": "timing"}],
    )
    assert result["sign_off_status"] == "CLEAR"


TESTS = [
    test_ambiguous_company_match_errors_instead_of_blending,
    test_specific_company_queries_still_resolve,
    test_variance_commentary_blocks_on_unconfirmed_material_variance,
    test_variance_commentary_clears_when_all_confirmed,
    test_reconciliation_blocks_on_duplicate_even_when_math_ties,
    test_reconciliation_clears_when_no_blockers_and_ties,
]


def main():
    passed, failed = 0, 0
    for test in TESTS:
        try:
            test()
            print(f"PASS  {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {test.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
