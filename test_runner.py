"""
Shared assert-based test runner for this repo's portfolio test suites
(no pytest dependency — see Forecasting_Agent/tests.py and
FPA_Copilot/tests.py for why). Extracted because both suites had an
identical copy-pasted runner (flagged by skylos as a duplicate).
"""


def run_tests(tests):
    passed, failed = 0, 0
    for test in tests:
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
