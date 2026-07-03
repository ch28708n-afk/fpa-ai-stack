# FP&A AI Stack

A driver-based forecasting agent, a dbt/DuckDB data layer, and an LLM
orchestrator ("copilot") that ties them together with a Month-End Close
toolkit's judgment logic — built as a portfolio project demonstrating
explainable, auditable AI applied to real FP&A workflows.

Built by [Charles Hassan](https://linkedin.com/in/charleshassan) — ~13-year
FP&A/finance-systems practitioner, now building AI-augmented finance tooling.

## The stack

```
SEC filings (20-F/6-K, 8-K/10-Q)
        |
        v
[1] Forecasting_Agent/    Driver-based revenue forecast + Confirmed-vs-
                          Hypothesis commentary. Non-ML, fully explainable —
                          every number traces to a named driver + citation.
        |
        v
[2] fpa_data_layer/       dbt + DuckDB turn the agent's output into a
                          tested (15 tests), refreshable, dashboarded
                          pipeline (Streamlit).
        |
        v
[3] FPA_Copilot/          An LLM (via OpenRouter) routes natural-language
                          requests to deterministic Python tools — the
                          forecast above, plus variance commentary and
                          reconciliation review logic adapted from a
                          Month-End Close Toolkit. Orchestrator-worker
                          pattern: the LLM routes and summarizes; it
                          never does the financial judgment itself.
```

## Why this design

Every stage is deliberately **non-black-box**. The forecast engine is a
weighted blend + a documented compounding-rate conversion, not a fitted
model. The commentary generator separates *Confirmed* facts (filed/guided)
from *Hypothesis* assumptions (extrapolated) and never states one as the
other. The Copilot's LLM only routes and summarizes — the reconciliation
and variance logic it calls into is plain, unit-tested Python.

This matters for two reasons: (1) it's how the judgment actually needs to
work in finance — an analyst has to be able to trace and challenge a number,
not just trust it — and (2) it's a stronger interview story than a clean
demo. See [Forecasting_Agent_CaseStudy.md](Forecasting_Agent_CaseStudy.md)
for a real bug caught mid-build (a YoY-vs-quarterly compounding error that
would have 5x'd a forecast) and the regression test written afterward so it
can't recur.

## Running it

Each subfolder has its own README with exact run instructions:
- [Forecasting_Agent/](Forecasting_Agent/) — `python run_forecast.py <company>_drivers.json`, tests via `python tests.py`
- [fpa_data_layer/](fpa_data_layer/) — see its README for the Python-version note (dbt needs 3.11, not the latest Python)
- [FPA_Copilot/](FPA_Copilot/) — `python orchestrator.py "your question here"`, tests via `python tests.py`

## Docs

- [Forecasting_Agent_Spec.md](Forecasting_Agent_Spec.md) — architecture spec written before the build
- [Forecasting_Agent_CaseStudy.md](Forecasting_Agent_CaseStudy.md) — the portfolio write-up, including the bug-catch and the generalization proof (2 companies, same code, zero changes)

## Status

All three phases are built, tested, and verified end-to-end — not just
specced. 24 automated assertions across the two test suites, 15 dbt tests,
and 3 manually-verified Copilot scenarios (single-tool routing, multi-tool
routing, out-of-scope refusal).
