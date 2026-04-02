import streamlit as st
import plotly.express as px
from connection import get_neo4j_driver
from analysis.queriesv2.block5_costs import Block5Queries

st.set_page_config(page_title="Cost & Mitigation Efficiency", layout="wide")
st.title("💰 Cost Analysis & Mitigation Efficiency")
st.markdown("""
Analysis of the **economic impact** of disruptions and the effectiveness 
of the responses applied to recover the supply chain.
""")

driver = get_neo4j_driver()

@st.cache_data(ttl=3600)
def load_block5_data():
    return Block5Queries.run_all(driver)

data = load_block5_data()

# --- 1. ECONOMIC BASELINE ---
st.header("1. Economic Impact of Disruptions")
if not data["disruption_cost_baseline"].empty:
    col1, col2, col3 = st.columns(3)
    
    # Extraiem mètriques per a ordres amb disrupció (is_disrupted = True)
    disrupted = data["disruption_cost_baseline"][data["disruption_cost_baseline"]['is_disrupted'] == True].iloc[0]
    
    with col1:
        st.metric("Avg. Shipping Cost (Disrupted)", f"${disrupted['avg_cost_usd']:,}")
    with col2:
        st.metric("Avg. Cost Premium", f"{disrupted['avg_cost_premium_pct']}%", delta="Disruption Penalty")
    with col3:
        st.metric("Avg. Delay Days", f"{disrupted['avg_delay_days']} days")

st.divider()

# --- 2. COST BY DISRUPTION TYPE ---
st.header("2. Financial Risk by Disruption Type")
if not data["cost_of_disruption_by_type"].empty:
    fig_cost = px.scatter(
        data["cost_of_disruption_by_type"],
        x="avg_cost_premium_pct",
        y="avg_delay_days",
        size="total_shipments",
        color="disruption_type",
        hover_name="disruption_type",
        title="Cost Premium vs. Delay Days by Disruption",
        labels={"avg_cost_premium_pct": "Avg. Cost Premium (%)", "avg_delay_days": "Avg. Delay (Days)"}
    )
    st.plotly_chart(fig_cost, use_container_width=True)

st.divider()

# --- 3. MITIGATION PERFORMANCE ---
st.header("3. Mitigation Effectiveness")
if not data["mitigation_action_summary"].empty:
    # Mostrem quines accions funcionen millor
    fig_mitigation = px.bar(
        data["mitigation_action_summary"],
        x="mitigation_action",
        y=["fully_effective", "partially_effective", "not_effective"],
        title="Effectiveness Count by Mitigation Action",
        barmode="group",
        labels={"value": "Number of Cases", "mitigation_action": "Action"}
    )
    st.plotly_chart(fig_mitigation, use_container_width=True)
    
    st.subheader("Efficiency Metrics Table")
    st.dataframe(
        data["mitigation_action_summary"][[
            "mitigation_action", "effectiveness_rate_pct", 
            "residual_delay_days", "recovered_within_schedule_pct"
        ]],
        use_container_width=True,
        hide_index=True
    )

st.divider()

# --- 4. THE EMERGENCY RESPONSE INDICATOR (EXPEDITED AIR) ---
st.header("4. Emergency Response Analysis (Expedited Air)")
if not data["expedited_air_usage"].empty:
    st.markdown("Usage of **Expedited Air Freight** as a reaction to critical disruptions.")
    fig_air = px.bar(
        data["expedited_air_usage"],
        x="disruption_type",
        y="expedited_air_share_pct",
        color="avg_cost_premium_when_expedited",
        title="Share of Expedited Air per Disruption Type",
        labels={"expedited_air_share_pct": "% of Cases using Air Freight"}
    )
    st.plotly_chart(fig_air, use_container_width=True)