"""AI commentary layer — narrates the multi-layer snapshot from tools.py.

Prompting approach borrowed directly from the Cowork Live Artifacts demo:
frame the system as a single analyst reasoning across sources, not a
dashboard displaying fragmented tools. Each data layer gets an explicit role
in the prompt rather than being dumped in as raw JSON. The LLM never
computes a number — every figure is already resolved by tools.py.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
MODEL = "anthropic/claude-haiku-4-5"

SYSTEM_PROMPT = """You are the FP&A analyst covering Meridian Motors Corp for
the current period. You are not a dashboard narrating disconnected metrics —
you are one analyst who has already reviewed three things this period: the
executive P&L summary, the revenue/cost variance bridge, and plant-level
operational signals. Your job is to connect them into one coherent read,
the way a real analyst would walk a CFO through "what happened and why."

Rules:
- Use ONLY the numbers given to you. Never invent or estimate a figure.
- Connect the layers where they actually relate (e.g., if a plant's defect
  rate or supplier lead time moved and that plausibly explains part of the
  cost variance, say so — but only if the data actually supports the link;
  don't force a connection that isn't there).
- Practitioner voice: dry, specific, no hype words. Write like a senior
  analyst's pre-read for a CFO meeting, not a marketing summary.
- 4-6 sentences. No headers, no bullet points.
"""


def generate_commentary(snapshot: dict) -> str:
    """Turn a tools.get_snapshot() dict into one connected analyst narrative."""
    pulse = snapshot["executive_pulse"]
    bridge = snapshot["variance_bridge"]
    mfg = snapshot["manufacturing"]

    revenue_line = (
        f"Revenue: ${pulse['revenue_actual']:,} actual vs ${pulse['revenue_budget']:,} budget "
        f"({pulse['revenue_variance_pct']:+.1f}%)"
    )
    margin_line = (
        f"Gross margin: {pulse['gross_margin_pct_actual']}% actual vs {pulse['gross_margin_pct_budget']}% budget "
        f"({pulse['margin_variance_pts']:+.1f} pts)"
    )
    units_line = (
        f"Units sold: {pulse['units_sold_actual']:,} actual vs {pulse['units_sold_budget']:,} budget "
        f"({pulse['unit_variance']:+,} units)"
    )
    rev_drivers = bridge["revenue_drivers"]
    revenue_drivers_line = (
        f"Revenue drivers: price {rev_drivers['price']:+,}, volume {rev_drivers['volume']:+,}, "
        f"mix {rev_drivers['mix']:+,} (largest: {bridge['largest_revenue_driver']})"
    )
    cost_drivers = bridge["cost_drivers"]
    cost_drivers_line = (
        f"Cost drivers: material {cost_drivers['material']:+,}, labor {cost_drivers['labor']:+,}, "
        f"freight {cost_drivers['freight']:+,} (largest: {bridge['largest_cost_driver']})"
    )
    plant_lines = "\n".join(
        f"{p['plant']}: {p['units_produced']:,} units, "
        f"defect rate {p['defect_rate_pct']}% ({p['defect_rate_delta']:+.2f} pts vs prior), "
        f"supplier lead time {p['supplier_lead_time_days']} days "
        f"({p['supplier_lead_time_delta']:+d} vs prior)"
        for p in mfg["plants"]
    )
    flagged_line = ", ".join(mfg["flagged_plants"]) if mfg["flagged_plants"] else "none"

    user_prompt = f"""{snapshot['company']} — {snapshot['period']} (as of {snapshot['as_of']})

LAYER 1 — Executive Pulse (top-line vs. budget):
{revenue_line}
{margin_line}
{units_line}

LAYER 2 — Variance Bridge (budget -> actual, driver by driver):
{revenue_drivers_line}
{cost_drivers_line}

LAYER 3 — Manufacturing/Supply Chain signals by plant:
{plant_lines}
Flagged plants (material degradation vs. prior period): {flagged_line}

Write the connected analyst read now."""

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
