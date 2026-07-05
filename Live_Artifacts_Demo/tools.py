"""Deterministic data-pull tools for the Live Artifacts portfolio demo.

Simulates a multi-source live feed (the way the real Variance Command Center
pulls from Gumroad + Beehiiv) using a local JSON file standing in for a
connected system (Drive/Airtable/ERP export). Swapping this file's loader
for a real API call is the only change needed to go from demo to production
data source — same pattern as the real Command Center build.

All financial computation (bridge math, deltas, flags) lives here in plain
Python. The LLM layer (commentary.py) only narrates numbers already computed.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent
DATA_SOURCES = {
    "current": DATA_DIR / "sample_data.json",
    "next_period (simulated refresh)": DATA_DIR / "sample_data_next_period.json",
}


def _load(source: str = "current"):
    return json.loads(DATA_SOURCES[source].read_text())


def get_executive_pulse(source: str = "current") -> dict:
    """Top-line snapshot: revenue, margin, and volume vs. budget."""
    executive_pulse = _load(source)["executive_pulse"]
    revenue_variance = executive_pulse["revenue_actual"] - executive_pulse["revenue_budget"]
    margin_variance_pts = round(
        executive_pulse["gross_margin_pct_actual"] - executive_pulse["gross_margin_pct_budget"], 1
    )
    unit_variance = executive_pulse["units_sold_actual"] - executive_pulse["units_sold_budget"]
    return {
        "revenue_actual": executive_pulse["revenue_actual"],
        "revenue_budget": executive_pulse["revenue_budget"],
        "revenue_variance": revenue_variance,
        "revenue_variance_pct": round(100 * revenue_variance / executive_pulse["revenue_budget"], 1),
        "gross_margin_pct_actual": executive_pulse["gross_margin_pct_actual"],
        "gross_margin_pct_budget": executive_pulse["gross_margin_pct_budget"],
        "margin_variance_pts": margin_variance_pts,
        "units_sold_actual": executive_pulse["units_sold_actual"],
        "units_sold_budget": executive_pulse["units_sold_budget"],
        "unit_variance": unit_variance,
    }


def get_variance_bridge(source: str = "current") -> dict:
    """Revenue and cost bridge: budget -> actual, driver by driver."""
    variance_bridge = _load(source)["variance_bridge"]
    revenue_drivers = {
        "price": variance_bridge["price_variance"],
        "volume": variance_bridge["volume_variance"],
        "mix": variance_bridge["mix_variance"],
    }
    cost_drivers = {
        "material": variance_bridge["material_cost_variance"],
        "labor": variance_bridge["labor_cost_variance"],
        "freight": variance_bridge["freight_cost_variance"],
    }
    largest_revenue_driver = max(revenue_drivers, key=lambda k: abs(revenue_drivers[k]))
    largest_cost_driver = max(cost_drivers, key=lambda k: abs(cost_drivers[k]))
    return {
        "revenue_budget": variance_bridge["revenue_budget"],
        "revenue_actual": variance_bridge["revenue_actual"],
        "revenue_drivers": revenue_drivers,
        "largest_revenue_driver": largest_revenue_driver,
        "cost_budget": variance_bridge["cost_budget"],
        "cost_actual": variance_bridge["cost_actual"],
        "cost_drivers": cost_drivers,
        "largest_cost_driver": largest_cost_driver,
    }


def get_manufacturing_signals(source: str = "current") -> dict:
    """Plant-level operational signals, flagging any material degradation."""
    plants = _load(source)["manufacturing"]["plants"]
    flagged = []
    for p in plants:
        defect_delta = round(p["defect_rate_pct"] - p["defect_rate_pct_prior"], 2)
        lead_time_delta = p["supplier_lead_time_days"] - p["supplier_lead_time_days_prior"]
        # Flag: defect rate up >0.3pt OR lead time up >3 days vs. prior period.
        if defect_delta > 0.3 or lead_time_delta > 3:
            flagged.append(p["name"])
    all_entries = [
        {
            "plant": p["name"],
            "units_produced": p["units_produced"],
            "defect_rate_pct": p["defect_rate_pct"],
            "defect_rate_delta": round(p["defect_rate_pct"] - p["defect_rate_pct_prior"], 2),
            "supplier_lead_time_days": p["supplier_lead_time_days"],
            "supplier_lead_time_delta": p["supplier_lead_time_days"] - p["supplier_lead_time_days_prior"],
        }
        for p in plants
    ]
    return {"plants": all_entries, "flagged_plants": flagged}


def get_snapshot(source: str = "current") -> dict:
    """One combined pull: everything the dashboard/commentary layer needs."""
    raw = _load(source)
    return {
        "company": raw["company"],
        "period": raw["period"],
        "as_of": raw["as_of"],
        "executive_pulse": get_executive_pulse(source),
        "variance_bridge": get_variance_bridge(source),
        "manufacturing": get_manufacturing_signals(source),
    }
