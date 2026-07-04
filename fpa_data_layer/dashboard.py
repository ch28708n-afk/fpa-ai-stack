"""
FP&A AI Stack — Data Layer dashboard.
Reads the dbt mart (fct_company_forecast) from the DuckDB warehouse and
renders a refreshable forecast view. Source -> dbt model -> this dashboard
is the full "Data Layer" pipeline (Phase 2 of the FP&A AI Stack roadmap).

Run: streamlit run dashboard.py
"""
from pathlib import Path

import duckdb
import streamlit as st

DB_PATH = str(Path(__file__).parent / "warehouse.duckdb")

st.set_page_config(page_title="FP&A Forecasting Agent — Data Layer", layout="wide")

st.title("FP&A Forecasting Agent — Data Layer")
st.caption(
    "Source: SEC filings (20-F/6-K, 8-K/10-Q) -> Python driver extraction -> "
    "dbt (staging + mart) -> this dashboard. Refresh by re-running "
    "load_raw.py + dbt run."
)

con = duckdb.connect(DB_PATH, read_only=True)
df = con.execute("SELECT * FROM main.fct_company_forecast ORDER BY company, quarter_index").df()
con.close()

companies = df["company"].unique().tolist()
selected = st.selectbox("Company", companies)

company_df = df[df["company"] == selected].reset_index(drop=True)

col1, col2, col3, col4 = st.columns(4)
first_row = company_df.iloc[0]
col1.metric("Base quarter", first_row["base_quarter"])
col2.metric("Trailing growth", f"{first_row['revenue_growth_trailing_pct']:.1f}%")
col3.metric("NDR", f"{first_row['ndr_overall_pct']:.0f}%", first_row["ndr_direction"])
col4.metric("Known data gaps", int(first_row["known_gaps_count"]))

st.subheader(f"8-Quarter Revenue Forecast — {selected}")

chart_df = company_df.set_index("quarter")[["low_musd", "base_case_musd", "high_musd"]]
chart_df.columns = ["Low", "Base Case", "High"]
st.line_chart(chart_df)

st.subheader("Forecast Detail")
display_df = company_df[[
    "quarter", "low_musd", "base_case_musd", "high_musd", "band_width_musd"
]].rename(columns={
    "quarter": "Quarter", "low_musd": "Low ($M)", "base_case_musd": "Base ($M)",
    "high_musd": "High ($M)", "band_width_musd": "Band Width ($M)"
})
st.dataframe(display_df, hide_index=True, width="stretch")

st.subheader("Driver Context")
driver_cols = st.columns(3)
driver_cols[0].metric("Gross margin", f"{first_row['gross_margin_pct']:.1f}%")
driver_cols[1].metric("RPO YoY growth", f"{first_row['total_rpo_yoy_pct']:.1f}%")
driver_cols[2].metric("NDR spread (enterprise vs overall)", f"{first_row['ndr_spread_pp']:.2f}pp")

st.caption(
    "All figures are driver-based projections, not guarantees. See "
    "Forecasting_Agent_Spec.md for methodology and Forecasting_Agent_CaseStudy.md "
    "for the full write-up including a caught-and-fixed compounding bug."
)
