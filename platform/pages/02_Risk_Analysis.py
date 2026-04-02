import streamlit as st
import plotly.express as px
from connection import get_neo4j_driver
from analysis.queriesv2 import Block2Queries

# 1. Page Setup
st.set_page_config(page_title="Risk Analysis", layout="wide")
st.title("⚠️ Multidimensional Risk Analysis")
st.markdown("""
This section explores how **Geopolitical** and **Weather** risk indices correlate 
with actual supply chain disruptions.
""")

# 2. Connection & Data Fetching
driver = get_neo4j_driver()

# We define sliders in the sidebar to filter 'Joint Risk' (Query 2.5)
st.sidebar.header("Risk Thresholds")
geo_thresh = st.sidebar.slider("Geopolitical Risk Threshold", 0.0, 1.0, 0.6)
weather_thresh = st.sidebar.slider("Weather Severity Threshold", 0.0, 1.0, 0.6)

@st.cache_data(ttl=600)
def load_block2_data(g_thresh, w_thresh):
    """
    Fetches Risk Data. 
    Note: joint_risk_exposure depends on the thresholds.
    """
    return Block2Queries.run_risk_pack(driver, geo_threshold=g_thresh, weather_threshold=w_thresh)

with st.spinner("Calculating risk correlations..."):
    data = load_block2_data(geo_thresh, weather_thresh)

# 3. Layout: Global Risk Distribution
st.header("1. Global Risk Profile")
col1, col2 = st.columns([1, 2])

with col1:
    # Distribution of Risk Levels (Low, Medium, High, Critical)
    fig_risk_dist = px.pie(
        data["risk_level_global"],
        values="total_shipments",
        names="risk_level",
        color="risk_level",
        color_discrete_map={
            'Low': '#2ca02c', 
            'Medium': '#ff7f0e', 
            'High': '#d62728', 
            'Critical': '#7f7f7f'
        },
        hole=0.4,
        title="Shipments by Risk Level"
    )
    st.plotly_chart(fig_risk_dist, use_container_width=True)

with col2:
    # Correlation between Risk Level and Disruption Rate
    fig_corr = px.bar(
        data["risk_level_global"],
        x="risk_level",
        y="disruption_rate_pct",
        text_auto='.2f',  
        labels={
            "disruption_rate_pct": "Disruption Rate (%)", 
            "risk_level": "Assigned Risk Level"
        },
        title="Risk Validation: Disruption Rate per Risk Level",
        template="plotly_white"
    )
    st.plotly_chart(fig_corr, use_container_width=True)

st.divider()

# 4. Layout: Risk by Dimension (Route & Product)
st.header("2. Risk Concentration")
tab1, tab2 = st.tabs(["By Route", "By Product Category"])

with tab1:
    fig_route_risk = px.bar(
        data["risk_exposure_by_route"],
        x="route",
        y="avg_combined_risk_score",
        color="disruption_rate_pct",
        labels={
            "route": "Logistics Route",
            "avg_combined_risk_score": "Avg Risk Score",
            "disruption_rate_pct": "Disruption %"
        },
        title="Average Combined Risk per Logistics Corridor",
        template="plotly_white"
    )
    st.plotly_chart(fig_route_risk, use_container_width=True)

with tab2:
    st.subheader("Product Category Vulnerability")
    st.dataframe(
        data["risk_exposure_by_product"],
        column_config={
            "product_category": "Category",
            "total_shipments": "Volume",
            "avg_combined_risk": st.column_config.NumberColumn("Avg Risk", format="%.2f"),
            "disruption_rate": st.column_config.ProgressColumn("Disruption Rate", min_value=0, max_value=1)
        },
        hide_index=True,
        use_container_width=True
    )

st.divider()

# 5. Layout: Joint Risk Exposure (The "What-If" preview)
st.header("3. High-Exposure Alert (Joint Risk)")
st.warning(f"Filtering orders with Geopolitical Risk > {geo_thresh} AND Weather Severity > {weather_thresh}")

if not data["joint_risk_exposure"].empty:
    col_a, col_b = st.columns(2)
    
    if 'total_shipments' in data["joint_risk_exposure"].columns:
        total_affected = data["joint_risk_exposure"]['total_shipments'].sum()
    else:
        total_affected = len(data["joint_risk_exposure"])
        
    col_a.metric("Total High-Risk Shipments", f"{int(total_affected):,}")
    col_a.metric("High-Risk Routes Found", len(data["joint_risk_exposure"]))
    
    column_name = 'avg_delay_days' 
    if column_name in data["joint_risk_exposure"].columns:
        avg_delay = data['joint_risk_exposure'][column_name].mean()
        col_b.metric("Avg. Delay in this Group", f"{avg_delay:.2f} days")
    else:
        col_b.metric("Avg. Delay", "N/A")
    
    st.write("### Detailed High-Risk Orders")
    st.dataframe(data["joint_risk_exposure"], use_container_width=True)
else:
    st.success("No orders currently match these high-risk criteria.")