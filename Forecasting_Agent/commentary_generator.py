"""
Commentary generator — turns the forecast engine's output into a sign-off-style
narrative. Same judgment discipline as the Month-End Close Toolkit: separates
Confirmed facts (filed/guided) from Hypothesis assumptions (extrapolated), and
raises a hard OPEN flag for anything not yet decomposed.
"""


def generate_commentary(drivers, forecast_result, quarter_index=0):
    driver_data = drivers["drivers"]
    q = forecast_result["quarters"][quarter_index]
    detail = forecast_result["growth_detail"]

    lines = []
    lines.append(
        f"FORECAST — {q['quarter']} Revenue: ${q['low_musd']}M – ${q['high_musd']}M "
        f"(base case ${q['base_case_musd']}M)\n"
    )
    lines.append("Drivers:")
    lines.append(
        f"- Trailing growth trend: {detail['trailing_avg']*100:.1f}% YoY "
        f"-> CONFIRMED (filed, {driver_data['revenue_growth_rate']['citation']})"
    )
    lines.append(
        f"- Guidance midpoint: {detail['guidance_mid']*100:.1f}% YoY "
        f"-> CONFIRMED (company guidance)"
    )
    ndr = driver_data["ndr"]
    lines.append(
        f"- NDR spread (enterprise {ndr['enterprise_100k_plus']*100:.0f}% vs overall "
        f"{ndr['overall']*100:.0f}%) nudges growth "
        f"{'up' if detail['nudge_applied'] >= 0 else 'down'} "
        f"{abs(detail['nudge_applied'])*100:.2f}pp -> HYPOTHESIS "
        f"(assumes enterprise mix-shift continues; no quarter-specific guidance on this)"
    )

    gaps = drivers.get("known_gaps", [])
    if gaps:
        lines.append("")
        lines.append("OPEN ITEMS:")
        for gap in gaps:
            lines.append(f"- {gap}")

    return "\n".join(lines)


if __name__ == "__main__":
    from forecast_engine import forecast_quarters, load_drivers

    drivers = load_drivers("mndy_drivers.json")
    result = forecast_quarters(drivers, n_quarters=8)
    print(generate_commentary(drivers, result, quarter_index=0))
