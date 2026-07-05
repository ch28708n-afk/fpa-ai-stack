"""Live Artifacts Demo — multi-layer FP&A analyst environment.

Portfolio piece answering Claude Cowork's "Live Artifacts" feature: same
outcome (one auto-refreshing analyst environment reasoning across sources)
built with Python + Streamlit + OpenRouter instead of Cowork's native tooling.

Run: streamlit run dashboard.py
"""

import streamlit as st
from commentary import generate_commentary
from tools import DATA_SOURCES, get_snapshot

WIDTH_STRETCH = "stretch"

st.set_page_config(page_title="Live Artifacts Demo — Meridian Motors Corp", layout="wide")

st.title("Live Artifacts Demo — Meridian Motors Corp")
st.caption(
    "Portfolio piece: same multi-source, auto-refreshing analyst environment "
    "Claude Cowork's Live Artifacts feature demoed, built with Python + Streamlit "
    "+ OpenRouter. Swap the data loader for a real API call to go live."
)

source = st.selectbox(
    "Simulate a live data refresh — switch the source, everything below recomputes",
    list(DATA_SOURCES.keys()),
)
if st.button("Refresh now"):
    st.cache_data.clear()


@st.cache_data(ttl=60)
def load_snapshot(source):
    return get_snapshot(source)


snapshot = load_snapshot(source)
pulse = snapshot["executive_pulse"]
bridge = snapshot["variance_bridge"]
mfg = snapshot["manufacturing"]

st.caption(f"{snapshot['company']} — {snapshot['period']} — as of {snapshot['as_of']}")

st.subheader("Layer 1 — Executive Pulse")
col1, col2, col3 = st.columns(3)
col1.metric(
    "Revenue",
    f"${pulse['revenue_actual']:,}",
    f"{pulse['revenue_variance_pct']:+.1f}% vs budget",
)
col2.metric(
    "Gross margin",
    f"{pulse['gross_margin_pct_actual']}%",
    f"{pulse['margin_variance_pts']:+.1f} pts vs budget",
)
col3.metric(
    "Units sold",
    f"{pulse['units_sold_actual']:,}",
    f"{pulse['unit_variance']:+,} vs budget",
)

st.subheader("Layer 2 — Variance Bridge")
bcol1, bcol2 = st.columns(2)
with bcol1:
    st.write("**Revenue drivers**")
    st.bar_chart(bridge["revenue_drivers"])
    st.dataframe(
        [{"driver": k, "amount": f"${v:+,}"} for k, v in bridge["revenue_drivers"].items()],
        hide_index=True,
        width=WIDTH_STRETCH,
    )
    st.caption(f"Largest driver: {bridge['largest_revenue_driver']}")
with bcol2:
    st.write("**Cost drivers**")
    st.bar_chart(bridge["cost_drivers"])
    st.dataframe(
        [{"driver": k, "amount": f"${v:+,}"} for k, v in bridge["cost_drivers"].items()],
        hide_index=True,
        width=WIDTH_STRETCH,
    )
    st.caption(f"Largest driver: {bridge['largest_cost_driver']}")

st.subheader("Layer 3 — Manufacturing / Supply Chain")
st.dataframe(mfg["plants"], hide_index=True, width=WIDTH_STRETCH)
if mfg["flagged_plants"]:
    st.warning(f"Flagged for material degradation vs. prior period: {', '.join(mfg['flagged_plants'])}")
else:
    st.success("No plants flagged this period.")

st.subheader("Connected analyst read")
with st.spinner("Generating commentary..."):
    try:
        st.write(generate_commentary(snapshot).replace("$", "\\$"))
    except Exception as e:
        st.info(f"Commentary unavailable right now ({e}). The data above is still live and correct.")
