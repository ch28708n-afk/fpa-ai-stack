# FP&A Forecasting Agent — Spec
_Day 5 · FP&A AI Stack · Phase 1 centerpiece. Data source: `MNDY_Financial_Extract.md` (monday.com, 20-F/6-K)._

---

## 1. Done Definition

**Done =** given a public SaaS company's filing data, produce a **driver-based revenue forecast for the next 4–8 quarters** + **auto-written variance commentary** explaining what's driving the forecast, with every number traceable back to a named driver and a filing location.

Not done = a black-box number. Every forecasted figure must answer "why" in one sentence citing a specific driver.

**Framing (per roadmap guardrail):** augmentation, not replacement. The agent proposes a driver-based forecast and shows its work — an analyst reviews, adjusts drivers, and owns the number. It never claims certainty it doesn't have.

---

## 2. Architecture

```
[1] FILINGS INPUT          [2] DRIVER MODEL          [3] FORECAST ENGINE       [4] COMMENTARY LAYER
  20-F / 6-K data      →     Extract + normalize   →    Quarter-by-quarter   →   Auto-written narrative
  (income statement,         key SaaS drivers            projection using          explaining each
  NDR, customer tiers,       (growth rate, NDR,           driver assumptions        driver's contribution,
  deferred rev, RPO)         margin, RPO coverage)        + confidence bands         flagged assumptions
```

**[1] Filings Input** — Structured extract (already done, Day 3): income statement, NDR/cohort data, deferred revenue, RPO, ASC 606 policy. This is the "ground truth" layer — nothing here is assumed.

**[2] Driver Model** — Converts raw filing data into a small set of named, explainable drivers (Section 3 below). Each driver has: a value, a trend (last 4-8 quarters), and a filing citation.

**[3] Forecast Engine** — Applies each driver forward using a simple, transparent method (not a black-box ML model): trend extrapolation with explicit assumption toggles (e.g., "NDR holds at 110%" or "NDR compresses to 108% per company guidance"). Produces point estimate + a range (best/base/worst) per quarter.

**[4] Commentary Layer** — Reuses the same judgment discipline as the Month-End Close Toolkit: Confirmed-vs-Hypothesis framing, materiality gating, and a sign-off gate that flags which assumptions are management-guided (Confirmed) vs. extrapolated (Hypothesis).

---

## 3. Key SaaS Drivers (explicit, mapped to MNDY filing data)

| # | Driver | MNDY Q1 2026 Value | Filing Location | Forecast Role |
|---|---|---|---|---|
| 1 | **Revenue growth rate (YoY)** | +24% | Income statement, 6-K | Primary top-line driver; base case = trailing-4Q average growth, decaying toward guidance |
| 2 | **Net Dollar Retention (NDR)** | 110% overall / 115-116% enterprise | MD&A, 6-K | Drives the "expansion" component of revenue — existing customer base compounding |
| 3 | **Gross margin** | 89% (stable) | Income statement | Held flat unless filing signals a shift (e.g., AI infra cost) |
| 4 | **Customer counts by ARR tier** ($100K+, $500K+) | 1,844 / 99, +39%/+74% YoY | MD&A, 6-K | Leading indicator for enterprise mix shift → informs NDR trend |
| 5 | **RPO / cRPO growth** | Total RPO +33% YoY, cRPO +26% YoY | MD&A, 6-K | Forward-looking check — RPO growing faster than revenue = accelerating pipeline, a confidence signal on the forecast |
| 6 | **Deferred revenue growth** | +20% YoY | Balance sheet, 6-K | Cross-check against revenue growth — should track within a few points; divergence flags a build/draw in the base |
| 7 | **Non-GAAP operating margin** | 14% (2025) → 11-12% (2026 guidance) | Income statement + guidance | Drives the profitability forecast alongside revenue |

**Why these seven:** each is (a) disclosed every quarter so the forecast is refreshable, (b) causally tied to revenue (not just correlated), and (c) traceable to a specific line in the extract — no driver here is invented.

---

## 4. Forecast Method (explainable, not ML)

For each quarter *t+1* through *t+8*:

```
Forecasted Revenue(t+1) = Revenue(t) × (1 + growth_rate_assumption)

growth_rate_assumption = blend of:
  - trailing 4Q actual growth rate (weighted 60%)
  - company FY guidance range, quarter-allocated (weighted 40%)
  - adjusted by NDR trend (if NDR rising, nudge growth up; if compressing, nudge down)

Confidence band = base case ± the historical variance between guided and actual
  (i.e., MNDY beat FY2025 non-GAAP op margin guidance by X bps → apply similar band)
```

This is deliberately simple and auditable — a weighted blend + a rule-based nudge, not a fitted model. The point is explainability: an interviewer or a controller can trace every forecasted number back to two inputs (trailing trend + guidance) and one driver-based adjustment (NDR).

---

## 5. Variance Commentary Output (example shape)

Reusing the Month-End Close Toolkit's judgment discipline:

```
FORECAST — Q2 2026 Revenue: $368M – $374M (base case $371M)

Drivers:
- Trailing-4Q growth trend: +24-25% YoY → CONFIRMED (filed, 6-K Q1 2026)
- FY2026 guidance quarter-allocated: implies ~$367M for Q2 → CONFIRMED (company guidance)
- NDR trend (110% stable, enterprise 115-116%) → nudges base case toward guidance midpoint
  rather than pure trend extrapolation → HYPOTHESIS (assumes NDR holds; no Q2-specific guidance)

⚠ OPEN: FX headwind (100-200 bps per guidance) not yet decomposed into revenue vs. margin
impact — flagged for analyst review before this forecast is used externally.
```

Same rules as the toolkit: never state a Hypothesis as a Confirmed fact; flag what's still open; refuse to present a forecast as "final" while an assumption is unresolved.

---

## 6. Data Readiness

All required inputs are already extracted and structured in `MNDY_Financial_Extract.md`:
- ✅ Income statement (quarterly, 5-quarter trend)
- ✅ NDR + cohort data
- ✅ Customer counts / ARR tier composition
- ✅ Deferred revenue + RPO/cRPO
- ✅ ASC 606 policy (confirms revenue recognition treatment — ratable, no lumpy recognition risk)
- ✅ 2026 guidance (revenue, margin, FCF ranges)

**Nothing further to pull before Week 2 build.** Week 2 implements: driver extraction script → forecast calculation → commentary generator, using this spec as the architecture doc.

---

## 7. What This Demonstrates (interview framing)

- Driver-based forecasting methodology, articulated and defensible (not "I ran a regression")
- SaaS unit-economics fluency (NDR, RPO/cRPO, deferred revenue mechanics, ASC 606)
- Explainable-AI design discipline: every output traceable to a named driver and a filing citation — no black box
- Augmentation framing carried through from the Month-End Close Toolkit into a second, more complex product — a consistent point of view across the whole portfolio

---

_Day 5 complete — 2026-07-03._
_Next: Week 2 build — implement the driver model + forecast engine + commentary generator per this spec._
