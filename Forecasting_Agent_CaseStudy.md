# The Variance — FP&A Forecasting Agent · Portfolio Case Study
_Built by Charles Hassan, 2026. Phase 1 centerpiece of the FP&A AI Stack. Data: public SEC filings (20-F/6-K, 8-K/10-Q press releases) for monday.com and Asana._

---

## One-page case study

**The problem.** Driver-based forecasting is one of the highest-value, most judgment-heavy skills in FP&A — and most "AI forecasting" demos are black boxes: a number comes out, with no visible reasoning, no citation to the filing, and no distinction between what's confirmed and what's assumed. That's not usable by a real finance team, and it doesn't hold up in an interview.

**What I built.** An FP&A Forecasting Agent: given a public company's extracted filing data, it produces an 8-quarter revenue forecast plus sign-off-style variance commentary. Four stages — filings input → driver model → forecast engine → commentary layer — each with a defined, auditable job. The forecast method is deliberately non-ML: a weighted blend of trailing growth and management guidance, nudged by a named driver (NDR trend), converted correctly from annual to quarterly compounding. Every number traces back to a driver, and every driver traces back to a citation.

**The impact.** Ran it against two real companies — monday.com (SaaS, expanding NDR, foreign private issuer) and Asana (SaaS, contracting NDR, domestic filer) — using only publicly filed data. Same code, zero changes, correct output on both, including handling a company (Asana) that's missing several data points MNDY discloses. The forecast doesn't paper over what it doesn't know: six open items are flagged in the Asana run alone, each naming exactly what's missing and why.

**Why it's augmentation, not replacement.** The agent proposes a forecast and shows its work — every driver, every assumption, every gap. An analyst reviews it, adjusts a driver if they disagree, and owns the number. It never claims a certainty it doesn't have, and it refuses to silently fill a data gap with an assumption disguised as a fact.

**What it demonstrates.** Driver-based forecasting methodology, articulated and defensible. SaaS unit-economics fluency (NDR, RPO/cRPO, deferred revenue mechanics, ASC 606). Explainable-system design — no black box. And genuine engineering discipline: I caught and fixed a real bug mid-build (see Example 2) rather than shipping a forecast that looked plausible but was wrong.

---

## Example 1 — Catching a Real Bug Mid-Build

**What happened:** the first version of the forecast engine took the filing's YoY growth rate (e.g., MNDY's 23%) and compounded it *quarter-over-quarter* instead of converting it to an equivalent quarterly rate. The result: MNDY's revenue projected to **5x in 2 years** ($351M → $1.87B by Q1 2028) — nowhere close to plausible for a company guided at 19-20% annual growth.

**The fix:** convert the annual rate to a quarterly compounding rate before applying it — `quarterly_rate = (1 + annual_rate)^0.25 - 1` — so 4 quarters of compounding equals the intended 1-year growth, not a 4x'd one.

```
BEFORE FIX                          AFTER FIX
Q1 2027: $810.6M (+130%)      →     Q1 2027: $433.0M (+23%)
Q1 2028: $1,870.6M (+433%)    →     Q1 2028: $533.6M (+52% cumulative, ~23%/yr)
```

**Why this matters for the portfolio:** anyone can wire an API to output a number. This is proof of catching a subtle, easy-to-miss unit error before it shipped — the same rigor a controller applies to a rec that "ties" but still hides a problem (see the Month-End Close Toolkit's Example 2).

---

## Example 2 — Generalization Proof (MNDY → Asana)

**The test:** build the pipeline once against monday.com's data, then run it — unmodified — against a second company with a materially different profile:

| | monday.com | Asana |
|---|---|---|
| NDR | 110% (expanding) | 97% (contracting) |
| Filer type | Foreign private issuer (20-F/6-K) | Domestic (10-K/10-Q, 8-K) |
| Data completeness | Full driver set disclosed | 6 data points missing or approximated |

**Result:** same code, zero changes, correct forecast for both. Asana's 8-quarter projection tracks its ~9% guided growth rate; MNDY's tracks its ~23%. The NDR-nudge driver correctly produces a near-zero adjustment for Asana (where enterprise-tier NDR isn't broken out, so the model defaults to zero rather than guessing) versus a real +0.75pp nudge for MNDY (where the enterprise/overall NDR spread is a disclosed, citable fact).

**Judgment encoded:** a missing data point becomes a flagged gap, not a silent assumption. Six such gaps are named explicitly in the Asana run — e.g., "$500K+ ARR tier not disclosed," "cRPO dollar figure not located, only growth rate known." The system tells you what it doesn't know instead of quietly guessing.

---

## Architecture Recap

```
[1] Filings Input  →  [2] Driver Model  →  [3] Forecast Engine  →  [4] Commentary Layer
   Structured JSON        7 named,              Weighted blend +        Confirmed-vs-
   per company             citable drivers        YoY→quarterly           Hypothesis
   (driver_schema_                                conversion +            narrative +
   template.json)                                 confidence band         open-items flag
```

Full architecture + driver definitions: [Forecasting_Agent_Spec.md](Forecasting_Agent_Spec.md). Working code: `Forecasting_Agent/` (forecast_engine.py, commentary_generator.py, run_forecast.py, driver_schema_template.json).

---

## Part of a Larger Stack

The Forecasting Agent isn't standalone — it's the centerpiece of a 4-piece FP&A AI Stack:

1. **Forecasting Agent** (this case study) — driver-based forecast + commentary, generalized across 2 companies
2. **Data Layer** (`fpa_data_layer/`) — DuckDB + dbt (15 tests) turn the agent's output into a refreshable, dashboarded pipeline (Streamlit)
3. **FPA Copilot** (`FPA_Copilot/`) — an LLM orchestrator routes natural-language requests to this agent plus two Month-End Close Toolkit-derived tools (variance commentary, reconciliation review), all in one interface
4. **Live Artifacts Demo** (`Live_Artifacts_Demo/`) — a continuously-connected, 3-layer analyst environment (P&L pulse, variance bridge, plant-level operational signals) whose refresh logic is proven by period-switching, with 9 regression tests

Full code for all four: see the project README at the repo root.

---

_Use: anchor a LinkedIn post, a portfolio-site page, and the interview story — especially the bug-catch example, which is a stronger signal than a clean demo would be._
_Created 2026-07-03. Companion to Forecasting_Agent_Spec.md and the Forecasting_Agent/ codebase._
