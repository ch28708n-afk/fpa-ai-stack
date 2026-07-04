"""
Entry point — runs the full pipeline: drivers -> forecast -> commentary.
Usage: python run_forecast.py [drivers_file.json]
Defaults to mndy_drivers.json. Any file matching driver_schema_template.json's
shape works — no code changes needed for a new company.
"""
import json
import sys

from commentary_generator import generate_commentary
from forecast_engine import forecast_quarters, load_drivers


def main():
    drivers_file = sys.argv[1] if len(sys.argv) > 1 else "mndy_drivers.json"
    drivers = load_drivers(drivers_file)
    result = forecast_quarters(drivers, n_quarters=8)

    print("=" * 70)
    print(f"FORECASTING AGENT — {drivers['company']}")
    print(f"Base quarter: {drivers['as_of_quarter']} (${result['base_revenue_musd']}M actual)")
    print(f"Applied growth rate: {result['growth_rate_applied']*100:.2f}% "
          f"(+/- {result['confidence_band_pp']}pp band)")
    print("=" * 70)
    print()
    print("8-QUARTER FORECAST TABLE")
    print(f"{'Quarter':<10} {'Low ($M)':>10} {'Base ($M)':>10} {'High ($M)':>10}")
    for q in result["quarters"]:
        print(f"{q['quarter']:<10} {q['low_musd']:>10} {q['base_case_musd']:>10} {q['high_musd']:>10}")
    next_quarter = result["quarters"][0]["quarter"]
    print()
    print(f"SAMPLE COMMENTARY — Next quarter ({next_quarter})")
    print("-" * 70)
    print(generate_commentary(drivers, result, quarter_index=0))
    print()

    # Save full output to file for portfolio use — named after the input file
    # so multiple companies don't clobber each other.
    output = {
        "forecast": result,
        "sample_commentary": generate_commentary(drivers, result, quarter_index=0),
    }
    out_name = drivers_file.replace("_drivers.json", "_forecast_output.json")
    with open(out_name, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved full output -> {out_name}")


if __name__ == "__main__":
    main()
