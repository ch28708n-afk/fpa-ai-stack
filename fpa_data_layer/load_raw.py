"""
Raw loader (the "EL" in ELT). Reads the driver + forecast JSON files already
produced by the Forecasting Agent and loads them into DuckDB as raw tables.
dbt then handles the "T" — staging models clean/flatten, marts combine.

Source data was pulled from SEC filings (20-F/6-K, 8-K/10-Q press releases) —
see MNDY_Financial_Extract.md and the Forecasting_Agent/*_drivers.json files
for provenance. This script does not call any live API; it's the boundary
between "manually-sourced filing data" and "the warehouse."
"""
import json
import duckdb
from pathlib import Path

FORECASTING_AGENT_DIR = Path(__file__).parent.parent / "Forecasting_Agent"
DB_PATH = Path(__file__).parent / "warehouse.duckdb"

DRIVER_FILES = ["mndy_drivers.json", "asana_drivers.json"]


def load_driver_file(path):
    with open(path, "r") as f:
        return json.load(f)


def flatten_drivers_row(data):
    drivers = data["drivers"]
    return {
        "company": data["company"],
        "as_of_quarter": data["as_of_quarter"],
        "revenue_growth_trailing_avg": drivers["revenue_growth_rate"]["trailing_avg"],
        "revenue_growth_guidance_lo": drivers["revenue_growth_rate"]["guidance_range"][0],
        "revenue_growth_guidance_hi": drivers["revenue_growth_rate"]["guidance_range"][1],
        "ndr_overall": drivers["ndr"]["overall"],
        "ndr_enterprise_100k_plus": drivers["ndr"]["enterprise_100k_plus"],
        "gross_margin": drivers["gross_margin"]["value"],
        "customers_100k_plus": drivers["customer_counts"]["over_100k_arr"]["value"],
        "customers_100k_plus_yoy_growth": drivers["customer_counts"]["over_100k_arr"]["yoy_growth"],
        "total_rpo_musd": drivers["rpo"]["total_rpo_musd"],
        "total_rpo_yoy_growth": drivers["rpo"]["total_rpo_yoy_growth"],
        "deferred_revenue_musd": drivers["deferred_revenue"]["current_musd"],
        "deferred_revenue_yoy_growth": drivers["deferred_revenue"]["yoy_growth"],
        "non_gaap_op_margin_prior_fy": drivers["non_gaap_operating_margin"]["prior_fy_actual"],
        "known_gaps_count": len(data.get("known_gaps", [])),
    }


def flatten_forecast_rows(company, forecast_output_path):
    with open(forecast_output_path, "r") as f:
        output = json.load(f)
    rows = []
    for q in output["forecast"]["quarters"]:
        rows.append({
            "company": company,
            "quarter": q["quarter"],
            "low_musd": q["low_musd"],
            "base_case_musd": q["base_case_musd"],
            "high_musd": q["high_musd"],
        })
    return rows


def _load_all_rows(driver_files):
    """Read each driver file + its matching forecast output, flattened for insert."""
    driver_rows = []
    forecast_rows = []

    for filename in driver_files:
        path = FORECASTING_AGENT_DIR / filename
        data = load_driver_file(path)
        driver_rows.append(flatten_drivers_row(data))

        forecast_output_name = filename.replace("_drivers.json", "_forecast_output.json")
        forecast_path = FORECASTING_AGENT_DIR / forecast_output_name
        if forecast_path.exists():
            forecast_rows.extend(flatten_forecast_rows(data["company"], forecast_path))
        else:
            print(f"WARNING: no forecast output found for {data['company']} at {forecast_path} "
                  f"— run Forecasting_Agent/run_forecast.py first.")

    return driver_rows, forecast_rows


def main():
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    driver_rows, forecast_rows = _load_all_rows(DRIVER_FILES)

    con.execute("DROP TABLE IF EXISTS raw.drivers")
    con.execute("""
        CREATE TABLE raw.drivers (
            company VARCHAR, as_of_quarter VARCHAR,
            revenue_growth_trailing_avg DOUBLE, revenue_growth_guidance_lo DOUBLE,
            revenue_growth_guidance_hi DOUBLE, ndr_overall DOUBLE,
            ndr_enterprise_100k_plus DOUBLE, gross_margin DOUBLE,
            customers_100k_plus INTEGER, customers_100k_plus_yoy_growth DOUBLE,
            total_rpo_musd DOUBLE, total_rpo_yoy_growth DOUBLE,
            deferred_revenue_musd DOUBLE, deferred_revenue_yoy_growth DOUBLE,
            non_gaap_op_margin_prior_fy DOUBLE, known_gaps_count INTEGER
        )
    """)
    for row in driver_rows:
        con.execute(
            "INSERT INTO raw.drivers VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            list(row.values())
        )

    con.execute("DROP TABLE IF EXISTS raw.forecast_quarters")
    con.execute("""
        CREATE TABLE raw.forecast_quarters (
            company VARCHAR, quarter VARCHAR,
            low_musd DOUBLE, base_case_musd DOUBLE, high_musd DOUBLE
        )
    """)
    for row in forecast_rows:
        con.execute(
            "INSERT INTO raw.forecast_quarters VALUES (?, ?, ?, ?, ?)",
            list(row.values())
        )

    print(f"Loaded {len(driver_rows)} company driver rows, {len(forecast_rows)} forecast-quarter rows.")
    print(f"Warehouse: {DB_PATH}")
    con.close()


if __name__ == "__main__":
    main()
