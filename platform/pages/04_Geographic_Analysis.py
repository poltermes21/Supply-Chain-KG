import streamlit as st
import plotly.express as px
from connection import get_neo4j_driver
from analysis.queriesv2 import Block4Queries

# 1. Page Configuration
st.set_page_config(page_title="Geographic Analysis", layout="wide")
st.title("🌍 Geographic Analysis & Community Detection")
st.markdown("""
This section identifies **Logistics Communities** using the Louvain algorithm. 
It reveals how the global network is organized into functional clusters.
""")

driver = get_neo4j_driver()

@st.cache_data(ttl=3600)
def load_block4_data():
    """Execute Louvain clustering and geographic flow queries."""
    with st.spinner("Detecting logistics communities..."):
        return Block4Queries.run_all(driver)

data = load_block4_data()

# 2. Community Structure (Louvain)
st.header("1. Logistics Clusters (Louvain Method)")
col1, col2 = st.columns([1, 2])

with col1:
    if not data["communities_by_city"].empty:
        # Group by community to see cluster sizes
        comm_summary = data["communities_by_city"].groupby('community_id').size().reset_index(name='city_count')
        fig_pie = px.pie(
            comm_summary, 
            values='city_count', 
            names='community_id',
            title="Distribution of Cities per Cluster",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.subheader("Community Search & Membership")
    search_query = st.text_input("Filter by city name:", "")
    df_comm = data["communities_by_city"]
    
    if search_query:
        df_comm = df_comm[df_comm['city'].str.contains(search_query, case=False)]
    
    st.dataframe(
        df_comm, 
        column_config={
            "community_id": "Cluster ID",
            "city": "City",
            "country": "Country"
        },
        use_container_width=True, 
        hide_index=True
    )

st.divider()

import plotly.graph_objects as go # Afegeix aquest import a dalt de tot

# 3. Inter-Community Connectivity
st.header("2. Inter-Cluster Flows")
st.markdown("Detailed flow volume between functional communities.")

if not data["inter_community_flows"].empty:
    df_sankey = data["inter_community_flows"]
    
    # Creem llistes úniques de nodes per a l'índex del Sankey
    all_nodes = list(set(df_sankey['from_community'].astype(str)) | set(df_sankey['to_community'].astype(str)))
    node_map = {node: i for i, node in enumerate(all_nodes)}
    
    fig_sankey = go.Figure(data=[go.Sankey(
        node = dict(
          pad = 15,
          thickness = 20,
          line = dict(color = "black", width = 0.5),
          label = [f"Cluster {n}" for n in all_nodes],
          color = "royalblue"
        ),
        link = dict(
          source = [node_map[str(x)] for x in df_sankey['from_community']],
          target = [node_map[str(x)] for x in df_sankey['to_community']],
          value = df_sankey['shipments'],
          color = "rgba(65, 105, 225, 0.4)",
          label = df_sankey['primary_route']
      ))])

    fig_sankey.update_layout(title_text="Global Community Traffic Backbone", font_size=12)
    st.plotly_chart(fig_sankey, use_container_width=True)
else:
    st.info("No inter-community flow data found.")

st.divider()

# 4. National Flow Exposure
st.header("3. National Flow Exposure")
if not data["country_flow_exposure"].empty:
    df_country = data["country_flow_exposure"].head(20)
    
    # Creem una columna calculada per al volum total (In + Out) per ordenar el gràfic
    df_country['total_volume'] = df_country['outbound'] + df_country['inbound']
    
    fig_country = px.bar(
        df_country,
        x=["outbound", "inbound"], # Gràfic de barres apilades o agrupades
        y="country",
        orientation='h',
        title="Top 20 Countries by Trade Volume (Outbound vs Inbound)",
        labels={
            "value": "Shipment Volume",
            "variable": "Flow Direction",
            "country": "Country"
        },
        color_discrete_map={
            "outbound": "#1f77b4", # Blau
            "inbound": "#ff7f0e"   # Taronja
        }
    )
    
    fig_country.update_layout(
        yaxis={'categoryorder':'total ascending'},
        legend_title="Type of Flow"
    )
    st.plotly_chart(fig_country, use_container_width=True)

    # Afegim una visualització dels percentatges en una taula expandible
    with st.expander("View Global Market Share by Country"):
        st.dataframe(
            data["country_flow_exposure"][["country", "region", "pct_outbound", "pct_inbound"]],
            column_config={
                "pct_outbound": st.column_config.ProgressColumn("Global Export %", format="%.2f%%", min_value=0, max_value=100),
                "pct_inbound": st.column_config.ProgressColumn("Global Import %", format="%.2f%%", min_value=0, max_value=100)
            },
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No country exposure data found.")