import streamlit as st
from connection import get_neo4j_driver
from analysis.queriesv2 import Block1Queries

# 1. Page Configuration (Must be the first Streamlit command)
st.set_page_config(
    page_title="Supply Chain Resilience KG",
    page_icon="🌐",
    layout="wide"
)

# 2. Initialize the Neo4j Driver
driver = get_neo4j_driver()

# 3. Hero Section (Landing Page Header)
st.title("🌐 Knowledge Graph-Based Supply Chain Architecture")
st.subheader("Decision Support System with Resilience Analysis")

st.markdown("""
This platform enables the exploration of global supply chain resilience through 
**Graph Analytics**. Powered by **Neo4j** and the **Graph Data Science (GDS)** library.
""")

st.divider()

# 4. Global Network Status (Data from Block 1)
st.header("📊 Global Network Health")

# We wrap the data fetching in a spinner for better UX
with st.spinner("Fetching operational baseline..."):
    # Executing the global KPIs query from your Block1Queries class
    kpi_data = Block1Queries.global_baseline_kpis(driver)

if not kpi_data.empty:
    # Extract the first row of data
    row = kpi_data.iloc[0]
    
    # Create four layout columns for the metrics
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Total Shipments", f"{int(row['total_orders']):,}")
    col2.metric("Delay Rate", f"{row['delay_rate_pct']}%", delta_color="inverse")
    col3.metric("Disruption Rate", f"{row['disruption_rate_pct']}%")
    col4.metric("Avg. Lead Time", f"{row['avg_actual_lead_time_days']} days")
else:
    st.error("No data found. Please check your Neo4j database content.")

st.info("👈 Use the sidebar to explore specific analysis blocks.")