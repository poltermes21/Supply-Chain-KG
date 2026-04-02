import streamlit as st
import plotly.express as px
from connection import get_neo4j_driver
from analysis.queriesv2 import Block1Queries

# 1. Page Setup
st.set_page_config(page_title="Operational Baseline", layout="wide")
st.title("📦 Operational Baseline Characterization")
st.markdown("Detailed overview of supply chain performance under normal and observed conditions.")

# 2. Connection & Data Fetching
driver = get_neo4j_driver()

@st.cache_data(ttl=600)  # Cache results for 10 minutes to improve speed
def load_block1_data():
    """Fetches all DataFrames required for Block 1."""
    return Block1Queries.run_all(driver)

with st.spinner("Analyzing graph patterns..."):
    data = load_block1_data()

# 3. Layout: Top Row (Shipment Distributions)
col1, col2 = st.columns(2)

with col1:
    st.subheader("Shipments by Logistics Route")
    # Using Plotly for better interactivity compared to standard st.bar_chart
    fig_route = px.bar(
        data["shipments_by_route"], 
        x="route", 
        y="total_shipments",
        color="total_shipments",
        labels={"route": "Logistic Corridor", "total_shipments": "Volume"},
        template="plotly_white"
    )
    st.plotly_chart(fig_route, use_container_width=True)

with col2:
    st.subheader("Transport Mode Split")
    fig_mode = px.pie(
        data["shipments_by_transport_mode"], 
        values="total_shipments", 
        names="transport_mode",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    st.plotly_chart(fig_mode, use_container_width=True)

st.divider()

# 4. Layout: Middle Row (Delays & Product Categories)
col3, col4 = st.columns([1, 2])

with col3:
    st.subheader("Delay Severity Distribution")
    # Helpful for identifying if delays are 'Minor' or 'Critical'
    st.dataframe(
        data["delay_severity_distribution"], 
        column_config={
            "severity": "Severity Level",
            "count": st.column_config.NumberColumn("Orders"),
            "pct": st.column_config.ProgressColumn("Percentage", min_value=0, max_value=100)
        },
        hide_index=True,
        use_container_width=True
    )

with col4:
    st.subheader("Product Category Volume & Delay Risk")
    fig_prod = px.scatter(
        data["shipments_by_product"],
        x="total_shipments",
        y="delay_rate_pct",
        size="total_shipments",
        color="product_category",
        hover_name="product_category",
        text="product_category",
        labels={
            "total_shipments": "Volume", 
            "delay_rate_pct": "Delay Rate (%)",
            "product_category": "Category"
        }
    )
    st.plotly_chart(fig_prod, use_container_width=True)

st.divider()

# 5. Layout: Bottom Row (Network Topology)
st.subheader("📍 Origin-Destination Redundancy")
st.info("This table identifies lanes with multiple routing options, indicating structural resilience.")
st.dataframe(data["od_redundancy_profile"], use_container_width=True, hide_index=True)