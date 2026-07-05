# Live Artifacts Demo

Portfolio piece answering Claude Cowork's "Live Artifacts" feature — an auto-refreshing analyst environment wired directly to live data (Drive/Airtable/Gmail in Cowork's case), reasoning across sources as one cohesive analyst rather than a set of fragmented dashboard widgets.

This demo reproduces the same outcome with Python + Streamlit + OpenRouter, on fictional data (Meridian Motors Corp):

- **`sample_data.json` / `sample_data_next_period.json`** — two "live source" snapshots (Q2 and Q3 2026). Standing in for a connected system; swapping the loader in `tools.py` for a real API call is the only change needed to go from demo to production, the same pattern the real [Variance Command Center](../../Cowork_OS/Side%20Hustle%20Lab/Finance%20Stack/Variance_Command_Center) build uses with actual Gumroad/Beehiiv data.
- **`tools.py`** — deterministic Python: revenue/margin variance, a full price/volume/mix and material/labor/freight cost bridge, and plant-level defect-rate/supplier-lead-time flagging. No LLM involved — every number here is computed and testable.
- **`commentary.py`** — the LLM layer (via OpenRouter). Prompted as one analyst connecting three layers, not narrating them separately — it's told to link a flagged plant's operational signals to the cost variance only when the data actually supports it, never to invent a number.
- **`dashboard.py`** — Streamlit UI: metrics, variance bridge charts + tables, plant signal table with an alert on flagged plants, and the connected AI narrative underneath. Includes a **data-source selector that actually demonstrates the refresh** — switching from Q2 to Q3 flips which plant gets flagged (Riverbend's supply issue resolves, a new one emerges at Coldwater), proving the flagging logic reacts to real data changes rather than being hardcoded to one company's numbers.
- **`tests.py`** — 7 regression tests: bridge math ties out exactly to the stated variance (not just plausible-looking), the flag flips correctly between periods, and a boundary test on the flagging threshold itself (catches off-by-one errors on `>` vs `>=`). Run: `python tests.py`.

## Run it

```
pip install -r requirements.txt
streamlit run dashboard.py
```

## Run the tests

```
python tests.py
```

## What it proves

Same reasoning pattern the Cowork Live Artifacts demo showed (multi-layer, auto-refreshing, one coherent analyst voice across sources) built without that specific product feature — showing both the from-scratch build (Forecasting Agent, Data Layer, Copilot elsewhere in this repo) and fluency with the newer native-tooling approach. The refresh simulation and test suite are the difference between *describing* "auto-refreshing" in a README and actually demonstrating it.
