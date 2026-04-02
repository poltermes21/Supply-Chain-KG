import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from connection import get_neo4j_driver
from analysis.queriesv2.block6_what_if import Block6Queries

# 1. Page Configuration
st.set_page_config(page_title="What-If Simulation", layout="wide")
st.title("🧪 What-If Analysis & Scenario Simulation")
st.markdown("""
Simulate network shocks and evaluate resilience by interacting with specific components of the Supply Chain.
""")

driver = get_neo4j_driver()

# --- SECTION 1: ROUTE SHOCK ---
st.header("1. Route Disruption Analysis")
col_r1, col_r2 = st.columns([1, 3])

with col_r1:
    st.subheader("Route Parameters")
    all_routes = ["Suez", "Pacific", "Intra-Asia", "Atlantic", "CoGH"]
    selected_routes = st.multiselect("Select Routes to Block:", all_routes, default=["Suez"])
    run_route = st.button("Simulate Route Shock")

with col_r2:
    if run_route or 'route_init' not in st.session_state:
        st.session_state['route_init'] = True
        route_results = Block6Queries.route_shock_overview(driver, selected_routes)
        reroute_results = Block6Queries.route_shock_reroutability(driver, selected_routes)
        
        if not route_results.empty:
            res = route_results.iloc[0]
            m1, m2, m3 = st.columns(3)
            m1.metric("Affected Shipments", f"{int(res['affected_shipments']):,}")
            m2.metric("Network Exposure", f"{res['pct_total_network']}%")
            m3.metric("Avg Lead Time", f"{res['avg_lead_time_days']} days")
            
            fig_sun = px.sunburst(
                reroute_results,
                path=['shock_status', 'origin', 'destination'],
                values='affected_shipments',
                color='shock_status',
                color_discrete_map={'stranded': '#EF553B', 'needs_rerouting': '#FECB52', 'partially_hedged': '#636EFA'},
                title="Reroutability Status"
            )
            st.plotly_chart(fig_sun, use_container_width=True)

st.divider()

# --- SECTION 2: HUB FAILURE ---
st.header("2. Critical Hub (Node) Failure")
col_n1, col_n2 = st.columns([1, 3])

with col_n1:
    st.subheader("Hub Parameters")
    city_input = st.text_input("Cities to Block (comma separated):", value="Shanghai")
    target_cities = [c.strip() for c in city_input.split(",") if c.strip()]
    run_node = st.button("Simulate Hub Failure")

with col_n2:
    if run_node or 'node_init' not in st.session_state:
        st.session_state['node_init'] = True
        node_results = Block6Queries.node_failure_global_impact(driver, blocked_cities=target_cities)
        
        if not node_results.empty:
            fig_node = px.bar(
                node_results.head(10),
                x="affected_shipments",
                y="destination",
                color="risk_score",
                title=f"Impacted Lanes from {', '.join(target_cities)}",
                orientation='h',
                color_continuous_scale="Reds"
            )
            st.plotly_chart(fig_node, use_container_width=True)
        else:
            st.warning("No incident flow found for selected cities.")

st.divider()

# --- SECTION 3: PATH OPTIMIZATION ---
st.header("3. Emergency Path Optimization (Dijkstra)")
col_p1, col_p2 = st.columns([1, 3])

with col_p1:
    st.subheader("Optimization Settings")
    src = st.text_input("Origin City:", value="Shanghai")
    dst = st.text_input("Destination City:", value="Rotterdam")
    weight = st.selectbox(
        "Optimize For:", 
        ["avg_lead_time_days", "avg_cost_usd", "avg_combined_risk_score"]
    )
    run_path = st.button("Find Optimal Route")

with col_p2:
    if run_path or 'path_init' not in st.session_state:
        st.session_state['path_init'] = True
        path_df = Block6Queries.shortest_path_by_weight(driver, src, dst, weight)
        
        if not path_df.empty:
            path_data = path_df.iloc[0]
            st.success(f"Optimal Path: {' → '.join(path_data['path_cities'])}")
            
            fig_path = go.Figure(go.Scatter(
                x=list(range(len(path_data['path_cities']))),
                y=[0] * len(path_data['path_cities']),
                mode='lines+markers+text',
                text=path_data['path_cities'],
                textposition="bottom center",
                marker=dict(size=25, color='#00CC96'),
                line=dict(width=3, color='#636EFA')
            ))
            fig_path.update_layout(height=250, xaxis_visible=False, yaxis_visible=False, margin=dict(l=20,r=20,t=40,b=20))
            st.plotly_chart(fig_path, use_container_width=True)
        else:
            st.error("No alternative path found between these nodes.")