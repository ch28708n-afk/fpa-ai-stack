"""
Forecast engine — driver-based revenue projection.
Method: weighted blend of trailing growth + guidance, nudged by NDR trend.
Deliberately non-ML: every number traces back to an explainable rule (see
Forecasting_Agent_Spec.md, Section 4).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from safe_io import read_json_file  # noqa: E402 — needs sys.path set up first


def load_drivers(path):
    # base_dir=cwd: this is the CLI-args entry point (run_forecast.py accepts a
    # user-supplied filename), so the enforced root is wherever the tool was invoked
    # from — matches the documented usage (run with a bare filename from that directory).
    return read_json_file(path, base_dir=Path.cwd())


def blended_growth_rate(drivers, trailing_weight=0.6, guidance_weight=0.4):
    driver_data = drivers["drivers"]
    trailing_avg = driver_data["revenue_growth_rate"]["trailing_avg"]
    guidance_lo, guidance_hi = driver_data["revenue_growth_rate"]["guidance_range"]
    guidance_mid = (guidance_lo + guidance_hi) / 2

    base_rate = trailing_weight * trailing_avg + guidance_weight * guidance_mid

    # NDR nudge: if enterprise NDR (115-116%) is meaningfully above overall NDR (110%),
    # nudge growth up slightly — enterprise mix-shift is a forward-looking tailwind.
    ndr_overall = driver_data["ndr"]["overall"]
    ndr_enterprise = driver_data["ndr"]["enterprise_100k_plus"]
    ndr_spread = ndr_enterprise - ndr_overall
    nudge = ndr_spread * 0.15  # damped — NDR spread is a signal, not a direct driver

    return base_rate + nudge, {
        "trailing_avg": trailing_avg,
        "guidance_mid": guidance_mid,
        "ndr_spread": ndr_spread,
        "nudge_applied": nudge,
    }


def confidence_band(base_rate, drivers):
    # Band width derived from the spread between trailing actuals and guidance —
    # a proxy for how much the company's own guidance has moved vs. trend.
    driver_data = drivers["drivers"]
    trailing_avg = driver_data["revenue_growth_rate"]["trailing_avg"]
    guidance_lo, guidance_hi = driver_data["revenue_growth_rate"]["guidance_range"]
    spread = abs(trailing_avg - guidance_hi)
    return max(spread, 0.02)  # floor at +/-2pp so the band is never zero


def forecast_quarters(drivers, n_quarters=8):
    as_of_key = drivers["as_of_quarter"].replace(" ", "_")  # "Q1 2026" -> "Q1_2026"
    base_revenue = drivers["quarterly_revenue"][as_of_key]["revenue_musd"]
    annual_growth_rate, growth_detail = blended_growth_rate(drivers)
    band_width = confidence_band(annual_growth_rate, drivers)

    # annual_growth_rate is a YoY figure (e.g. 23% more than the same quarter a year
    # ago) — NOT a quarter-over-quarter rate. Compounding it QoQ would 5x revenue in
    # 2 years, which is wrong. Convert to the equivalent quarterly compounding rate:
    # (1 + q)^4 = 1 + annual  =>  q = (1 + annual)^0.25 - 1
    quarterly_rate = (1 + annual_growth_rate) ** 0.25 - 1
    quarterly_rate_low = (1 + annual_growth_rate - band_width) ** 0.25 - 1
    quarterly_rate_high = (1 + annual_growth_rate + band_width) ** 0.25 - 1

    quarters = []
    revenue = base_revenue
    revenue_low = base_revenue
    revenue_high = base_revenue

    quarter_labels = _future_quarter_labels(as_of_key, n_quarters)

    for label in quarter_labels:
        revenue = revenue * (1 + quarterly_rate)
        revenue_low = revenue_low * (1 + quarterly_rate_low)
        revenue_high = revenue_high * (1 + quarterly_rate_high)
        quarters.append({
            "quarter": label,
            "base_case_musd": round(revenue, 1),
            "low_musd": round(revenue_low, 1),
            "high_musd": round(revenue_high, 1),
        })

    return {
        "base_revenue_musd": base_revenue,
        "growth_rate_applied": round(annual_growth_rate, 4),
        "quarterly_rate_applied": round(quarterly_rate, 4),
        "growth_detail": growth_detail,
        "confidence_band_pp": round(band_width * 100, 2),
        "quarters": quarters,
    }


def _future_quarter_labels(start_label, n):
    # start_label like "Q1_2026" -> generate n subsequent quarter labels
    q, year = start_label.split("_")
    q_num = int(q[1])
    year = int(year)
    labels = []
    for _ in range(n):
        q_num += 1
        if q_num > 4:
            q_num = 1
            year += 1
        labels.append(f"Q{q_num} {year}")
    return labels


if __name__ == "__main__":
    drivers = load_drivers("mndy_drivers.json")
    result = forecast_quarters(drivers, n_quarters=8)
    print(json.dumps(result, indent=2))
