import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from shared.connection import get_neo4j_driver
from analysis.queriesv2.block6_what_if import Block6Queries
from shared.ui_helpers import render_section_header
from shared.pyvis_helpers import apply_pyvis_post_processing, render_pyvis_html
from shared.colors import SHOCK_STATUS_COLORS

st.set_page_config(page_title="What-If Scenarios", layout="wide")

FONT_SANS   = "IBM Plex Sans, sans-serif"
FONT_MONO   = "IBM Plex Mono, monospace"
GRID_COLOR  = "#2A2D3A"
AXIS_COLOR  = "#6B7280"
TEXT_COLOR  = "#E5E7EB"
TRANSPARENT = "rgba(0,0,0,0)"

# Display labels are page-local (UI strings); colours come from the shared
# palette so they stay aligned with any other view that uses shock status.
SHOCK_STATUS = {
    "fully_blocked": {"label": "Fully blocked",        "color": SHOCK_STATUS_COLORS["fully_blocked"]},
    "primary_loss":  {"label": "Primary route lost",   "color": SHOCK_STATUS_COLORS["primary_loss"]},
    "partial_loss":  {"label": "Secondary route lost", "color": SHOCK_STATUS_COLORS["partial_loss"]},
}

WEIGHT_LABELS = {
    "avg_lead_time_days":      "Lead Time (days)",
    "avg_cost_usd":            "Cost (USD)",
    "avg_combined_risk_score": "Risk Score",
}

ALL_ROUTES = ["Suez", "Pacific", "Intra-Asia", "Atlantic", "CoGH"]
ALL_CITIES = ["Shanghai", "Rotterdam", "Singapore", "Hamburg", 
              "Los Angeles", "Shenzhen","Busan", "New York", "Mumbai", 
              "Tokyo", "Santos", "Felixstowe", "Antwerp"]
SOURCE_CITIES = ["Shanghai", "Rotterdam", "Singapore", "Hamburg", "Los Angeles", 
                 "New York", "Tokyo", "Santos", "Felixstowe", "Antwerp"]
TARGET_CITIES = ["Shanghai", "Rotterdam", "Singapore", "Hamburg",
                 "Shenzhen","Busan", "Mumbai", "Tokyo", "Santos"]
CRITICAL_HUBS = {"Shanghai", "Rotterdam", "Singapore"}


def _is_neo4j_connection_error(exc: Exception) -> bool:
    """Identify connection-refused/unavailable errors from Neo4j driver calls."""
    error_text = str(exc)
    markers = (
        "Couldn't connect",
        "WinError 10061",
        "Connection refused",
        "ServiceUnavailable",
        "Failed to establish connection",
    )
    return any(marker in error_text for marker in markers)


def _show_neo4j_unavailable_warning():
    st.warning(
        "What-If simulation is unavailable because the Neo4j database is not running "
        "or cannot be reached. You can retry anytime with the Run buttons."
    )

def base_layout(**kwargs):
    defaults = dict(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font=dict(family=FONT_SANS, color=TEXT_COLOR),
        hoverlabel=dict(
            bgcolor="#1A1D27", bordercolor="#374151",
            font=dict(family=FONT_SANS, size=12, color=TEXT_COLOR),
        ),
    )
    defaults.update(kwargs)
    return defaults

def styled_xaxis(**kwargs):
    d = dict(
        gridcolor=GRID_COLOR, linecolor="#3D4151",
        tickfont=dict(family=FONT_SANS, size=10, color=AXIS_COLOR),
        title_font=dict(family=FONT_SANS, size=11, color=AXIS_COLOR),
        zeroline=False,
    )
    d.update(kwargs)
    return d

def styled_yaxis(**kwargs):
    d = dict(
        gridcolor=GRID_COLOR, linecolor="#3D4151",
        tickfont=dict(family=FONT_SANS, size=10, color=AXIS_COLOR),
        title_font=dict(family=FONT_SANS, size=11, color=AXIS_COLOR),
        zeroline=False,
    )
    d.update(kwargs)
    return d


# Severity ranking — used to pick a node's color when it sits on multiple
# affected lanes (worst status wins).
_STATUS_SEVERITY = {"fully_blocked": 3, "primary_loss": 2, "partial_loss": 1}


def _build_pyvis_route_shock(df_reroute, df_all_flow, all_cities, status_palette):
    """Network of OD lanes after a route blockade, on top of the full topology.

    The full CITY_FLOW network is drawn as a faint grey backdrop so the user
    can see context. Affected lanes (from `df_reroute`) are then overlaid in
    their shock-status colour. Nodes are coloured by the worst status touching
    them and sized by the total affected orders incident to the city.
    """
    from pyvis.network import Network

    net = Network(
        height="500px", width="100%",
        bgcolor="#0F1117", font_color="#F9FAFB",
        directed=True, notebook=False, cdn_resources="remote",
    )
    net.set_options("""
    {
      "nodes": {
        "borderWidth": 2, "borderWidthSelected": 3,
        "font": {"size": 14, "face": "IBM Plex Sans", "color": "#F9FAFB"}
      },
      "edges": {
        "smooth": {"enabled": true, "type": "dynamic", "roundness": 0.3},
        "selectionWidth": 1.5
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -3000, "centralGravity": 0.3,
          "springLength": 150, "springConstant": 0.05,
          "damping": 0.2, "avoidOverlap": 0.45
        },
        "minVelocity": 0.6, "solver": "barnesHut",
        "stabilization": {"enabled": true, "iterations": 200, "fit": true}
      },
      "interaction": {
        "hover": true, "dragNodes": true, "zoomView": true,
        "tooltipDelay": 80, "navigationButtons": true
      }
    }
    """)

    # Aggregate per-city: worst status touching it, total affected orders.
    city_worst_status = {}     # city -> shock_status
    city_affected_orders = {}  # city -> int
    city_lane_count = {}       # city -> int
    if not df_reroute.empty:
        for _, r in df_reroute.iterrows():
            for endpoint in (r["origin"], r["destination"]):
                cur = city_worst_status.get(endpoint)
                if cur is None or _STATUS_SEVERITY[r["shock_status"]] > _STATUS_SEVERITY[cur]:
                    city_worst_status[endpoint] = r["shock_status"]
                city_affected_orders[endpoint] = (
                    city_affected_orders.get(endpoint, 0) + int(r["affected_orders"])
                )
                city_lane_count[endpoint] = city_lane_count.get(endpoint, 0) + 1

    max_city_orders = max(city_affected_orders.values(), default=1) or 1

    for city in all_cities:
        status = city_worst_status.get(city)
        affected = city_affected_orders.get(city, 0)
        lanes = city_lane_count.get(city, 0)
        if status is None:
            color = "#3D4151"  # untouched: dim grey
            size = 14
            status_label = "Unaffected"
        else:
            color = status_palette[status]["color"]
            size = 18 + 26 * (affected / max_city_orders)
            status_label = status_palette[status]["label"]
        net.add_node(
            city, label=city,
            color={"background": color, "border": "#0F1117",
                   "highlight": {"background": color, "border": "#F9FAFB"}},
            size=size,
            title=(f"<b>{city}</b><br>"
                   f"Worst status: {status_label}<br>"
                   f"Affected orders: {affected:,}<br>"
                   f"Affected lanes: {lanes}"),
        )

    # Faint backdrop: all CITY_FLOW edges that are NOT in the affected set.
    affected_pairs = set()
    if not df_reroute.empty:
        affected_pairs = {(r["origin"], r["destination"])
                          for _, r in df_reroute.iterrows()}
    if df_all_flow is not None and not df_all_flow.empty:
        for _, r in df_all_flow.iterrows():
            u, v = r["origin"], r["destination"]
            if (u, v) in affected_pairs:
                continue
            net.add_edge(
                u, v,
                color={"color": "rgba(140,140,160,0.18)",
                       "hover": "rgba(180,180,200,0.45)"},
                width=1,
                arrows={"to": {"enabled": True, "scaleFactor": 0.45}},
                title=(f"<b>{u} &rarr; {v}</b><br>"
                       f"Orders: {int(r['orders']):,}<br>"
                       f"Not affected"),
                physics=True,
            )

    # Affected lanes overlaid on top, coloured by shock status.
    if not df_reroute.empty:
        max_orders = int(df_reroute["affected_orders"].max()) or 1
        for _, r in df_reroute.iterrows():
            u, v = r["origin"], r["destination"]
            status = r["shock_status"]
            color = status_palette[status]["color"]
            orders = int(r["affected_orders"])
            width = 1.5 + 4 * (orders / max_orders)
            is_severed = status == "fully_blocked"
            blocked_list = r.get("blocked_routes") or []
            surviving_list = r.get("surviving_routes") or []
            primary = r.get("primary_route") or "—"
            blocked_str = ", ".join(blocked_list) if len(blocked_list) else "—"
            surviving_str = ", ".join(surviving_list) if len(surviving_list) else "none"
            lane_total = int(r.get("lane_total_orders", orders))
            share_pct = float(r.get("affected_order_share_pct", 0))
            net.add_edge(
                u, v,
                color={"color": color, "hover": color, "highlight": color},
                width=width,
                dashes=is_severed,
                arrows={"to": {"enabled": True, "scaleFactor": 0.8}},
                title=(f"<b>{u} &rarr; {v}</b><br>"
                       f"Status: {status_palette[status]['label']}<br>"
                       f"Affected orders: {orders:,} of {lane_total:,} "
                       f"({share_pct:.1f}% of lane volume)<br>"
                       f"Primary route: {primary}<br>"
                       f"Blocked routes: {blocked_str}<br>"
                       f"Surviving routes: {surviving_str}"),
                physics=True,
            )

    return apply_pyvis_post_processing(net.generate_html(notebook=False))

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main, .stApp {
    background-color: #0F1117 !important;
    color: #E5E7EB !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}
[data-testid="stSidebar"] { background-color: #1A1D27 !important; }
p, li, span, label, div   { color: #E5E7EB; font-family: 'IBM Plex Sans', sans-serif; }
h1, h2, h3 { color: #F9FAFB !important; font-family: 'IBM Plex Sans', sans-serif !important; }

.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.67rem; font-weight: 600;
    letter-spacing: 0.14em; text-transform: uppercase;
    color: #6B7280; margin-bottom: 0.3rem;
}
.section-title {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.2rem; font-weight: 700; color: #F9FAFB;
    margin-bottom: 1rem;
    border-left: 3px solid #F59E0B; padding-left: 0.75rem;
    line-height: 1.3;
}
.divider-line { border: none; border-top: 1px solid #2A2D3A; margin: 1.5rem 0; }

/* KPI impact card */
.impact-card {
    background: #1A1D27; border: 1px solid #2A2D3A;
    border-radius: 8px; padding: 0.85rem 1rem;
    margin-bottom: 0.35rem; border-left-width: 3px;
}
.ic-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem; font-weight: 600;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: #6B7280; margin-bottom: 0.15rem;
}
.ic-value { font-size: 1.35rem; font-weight: 700; color: #F9FAFB; line-height: 1.1; }
.ic-sub   { font-size: 0.72rem; color: #9CA3AF; margin-top: 0.2rem;
            font-family: 'IBM Plex Mono', monospace; }

/* Callouts */
.callout-critical {
    background: #1E0F0F; border: 1px solid #7F1D1D;
    border-left: 4px solid #EF4444; border-radius: 6px;
    padding: 0.8rem 1rem; margin: 0.5rem 0 1rem 0;
    font-size: 0.84rem; color: #FCA5A5; line-height: 1.6;
}
.callout-critical strong { font-family: 'IBM Plex Mono', monospace; color: #EF4444; }
.callout-warn {
    background: #1C1A0F; border: 1px solid #78350F;
    border-left: 4px solid #F59E0B; border-radius: 6px;
    padding: 0.8rem 1rem; margin: 0.5rem 0 1rem 0;
    font-size: 0.84rem; color: #FCD34D; line-height: 1.6;
}
.callout-warn strong { font-family: 'IBM Plex Mono', monospace; color: #F59E0B; }

/* Preset button strip */
.preset-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem; font-weight: 600;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: #6B7280; margin-bottom: 0.4rem;
}

/* Path node */
.path-node {
    display: inline-block;
    background: #1A1D27; border: 1px solid #2A2D3A;
    border-radius: 6px; padding: 0.35rem 0.7rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem; font-weight: 600; color: #F9FAFB;
}
.path-arrow {
    display: inline-block; color: #4B5563;
    font-size: 1rem; margin: 0 0.3rem;
    font-family: 'IBM Plex Sans', sans-serif;
}
.path-row { margin-bottom: 0.6rem; line-height: 2.2; }
.path-weight-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.1em;
    margin-bottom: 0.25rem;
}

[data-testid="stDataFrame"] * { font-family: 'IBM Plex Sans', sans-serif !important; }
[data-testid="stSelectbox"] label, [data-testid="stMultiSelect"] label {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important; color: #6B7280 !important;
    text-transform: uppercase; letter-spacing: 0.08em;
}
</style>
""", unsafe_allow_html=True)


# HEADER
st.markdown('<div class="section-label">Block 6</div>', unsafe_allow_html=True)
st.markdown("# What-If Scenario Simulation")
st.markdown(
    "Simulate network shocks — route blockages, hub failures and path optimization — "
    "to quantify resilience and identify rerouting alternatives."
)
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

driver = get_neo4j_driver()
what_if_db_unavailable = st.session_state.get("what_if_db_unavailable", False)
what_if_db_unavailable_tab = st.session_state.get("what_if_db_unavailable_tab")

# TABS
tab_route, tab_node, tab_path = st.tabs([
    "Route Shock",
    "Node Failure",
    "Path Optimization",
])



# SECTION 1 - Route Shock

with tab_route:
    render_section_header("Route Shock Simulation")

    if what_if_db_unavailable and what_if_db_unavailable_tab == "route":
        _show_neo4j_unavailable_warning()

    # Presets
    st.markdown('<div class="preset-label">Quick Presets</div>', unsafe_allow_html=True)
    pre_c1, pre_c2, pre_c3, pre_c4 = st.columns(4)
    preset_route = None
    with pre_c1:
        if st.button("Suez Blockage", width='stretch'):
            preset_route = ["Suez"]
    with pre_c2:
        if st.button("Suez + Intra-Asia", width='stretch'):
            preset_route = ["Suez", "Intra-Asia"]
    with pre_c3:
        if st.button("Pacific + Atlantic", width='stretch'):
            preset_route = ["Pacific", "Atlantic"]
    with pre_c4:
        if st.button("All routes", width='stretch'):
            preset_route = ALL_ROUTES

    if preset_route is not None:
        st.session_state["blocked_routes"] = preset_route
        st.rerun()

    default_routes = st.session_state.get("blocked_routes", ["Suez"])
    blocked_routes = st.multiselect(
        "Blocked routes",
        options=ALL_ROUTES,
        default=default_routes,
    )

    run_route = st.button(
        "▶ Run Route Shock",
        type="primary",
        width='content',
    )

    # Only query and store results when button is pressed
    if run_route:
        if not blocked_routes:
            st.session_state["route_results"] = None
            st.session_state["route_blocked"] = []
        else:
            with st.spinner("Simulating route shock..."):
                try:
                    df_overview = Block6Queries.route_shock_overview(driver, blocked_routes)
                    df_reroute  = Block6Queries.route_shock_reroutability(driver, blocked_routes)
                    df_penalty  = Block6Queries.route_shock_penalty_estimate(driver, blocked_routes)
                    df_all_flow = Block6Queries.all_city_flow(driver)
                    st.session_state["what_if_db_unavailable"] = False
                    st.session_state["what_if_db_unavailable_tab"] = None
                    st.session_state["route_results"] = (df_overview, df_reroute, df_penalty, df_all_flow)
                    st.session_state["route_blocked"] = blocked_routes
                except Exception as exc:
                    if _is_neo4j_connection_error(exc):
                        st.session_state["what_if_db_unavailable"] = True
                        st.session_state["what_if_db_unavailable_tab"] = "route"
                        _show_neo4j_unavailable_warning()
                    else:
                        st.warning(
                            "Route shock simulation is temporarily unavailable. "
                            "Please try again."
                        )

    # Render stored results (only if they exist)
    if st.session_state.get("route_results") is not None:
        df_overview, df_reroute, df_penalty, df_all_flow = st.session_state["route_results"]
        displayed_routes = st.session_state.get("route_blocked", blocked_routes)

        if df_overview.empty:
            st.info("The selected blockade does not affect any active orders.")
        else:
            ov = df_overview.iloc[0]

            # Callout
            pct = float(ov["pct_total_network"])
            if pct >= 30:
                st.markdown(f"""
                <div class="callout-critical">
                    <strong>⚠ Critical Impact — {pct:.1f}% of network affected</strong><br>
                    Blocking <strong>{', '.join(displayed_routes)}</strong> would affect
                    <strong>{int(ov['affected_orders']):,} orders</strong>.
                    This is a first-order disruption requiring immediate activation of alternative routes.
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="callout-warn">
                    <strong>⚠ Moderate Impact — {pct:.1f}% of network affected</strong><br>
                    Blocking <strong>{', '.join(displayed_routes)}</strong> would affect
                    <strong>{int(ov['affected_orders']):,} orders</strong>.
                </div>""", unsafe_allow_html=True)

            # KPI cards
            k1, k2 = st.columns(2)
            kpi_data = [
                (k1, "Affected Orders",   f"{int(ov['affected_orders']):,}", "#EF4444",
                 "out of total network"),
                (k2, "% Network Exposed",    f"{pct:.1f}%",                        "#F59E0B",
                 "of total volume")
            ]
            for col, label, val, color, sub in kpi_data:
                with col:
                    st.markdown(f"""
                    <div class="impact-card" style="border-left-color:{color}">
                        <div class="ic-label">{label}</div>
                        <div class="ic-value" style="color:{color}">{val}</div>
                        <div class="ic-sub">{sub}</div>
                    </div>""", unsafe_allow_html=True)

            st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

            # Reroutability network + stranded table
            if not df_reroute.empty:
                col_san, col_strand = st.columns([3, 2])

                with col_san:
                    st.markdown('<div class="section-label">Reroutability — affected network</div>',
                                unsafe_allow_html=True)

                    # Legend
                    leg_cols = st.columns(len(SHOCK_STATUS))
                    for i, (key, meta) in enumerate(SHOCK_STATUS.items()):
                        with leg_cols[i]:
                            st.markdown(f"""
                            <div style="display:flex;align-items:flex-start;gap:0.5rem;margin-bottom:0.75rem">
                                <div style="min-width:10px;height:10px;border-radius:2px;
                                            background:{meta['color']};margin-top:3px;flex-shrink:0"></div>
                                <div>
                                    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;
                                                font-weight:600;color:{meta['color']};letter-spacing:0.05em">
                                        {meta['label']}
                                    </div>
                                </div>
                            </div>""", unsafe_allow_html=True)

                    try:
                        route_html = _build_pyvis_route_shock(
                            df_reroute, df_all_flow, ALL_CITIES, SHOCK_STATUS,
                        )
                        render_pyvis_html(route_html, height=520)
                        st.caption(
                            "Coloured arrows = affected lanes (width ∝ affected orders, "
                            "dashed = no surviving route) · "
                            "Faint arrows = unaffected lanes (full topology backdrop) · "
                            "Node color = worst status touching the city, size ∝ affected orders. "
                            "Hover an affected lane to see primary / blocked / surviving routes."
                        )
                    except ModuleNotFoundError:
                        st.warning("PyVis is not installed. Run `pip install pyvis` to enable this view.")
                    except Exception as e:
                        st.warning(f"Could not render network: {e}")

                with col_strand:
                    st.markdown('<div class="section-label">Lanes by shock status</div>',
                                unsafe_allow_html=True)

                    status_options = ["All"] + [v["label"] for v in SHOCK_STATUS.values()]
                    status_filter = st.selectbox(
                        "Filter by status",
                        options=status_options,
                        index=0,
                        key="status_filter",
                    )
                    df_rr_disp = df_reroute.copy()
                    
                    label_to_key = {v["label"]: k for k, v in SHOCK_STATUS.items()}
                    if status_filter != "All":
                        selected_key = label_to_key[status_filter]
                        df_rr_disp = df_rr_disp[df_rr_disp["shock_status"] == selected_key]

                    df_rr_disp["blocked_pct"] = (
                        df_rr_disp["blocked_route_count"] / df_rr_disp["total_routes"] * 100
                    )
                    df_rr_disp["shock_status"] = df_rr_disp["shock_status"].map(
                        {k: v["label"] for k, v in SHOCK_STATUS.items()}
                    )
                    
                    df_rr_disp = df_rr_disp[[
                        "origin", "destination", "shock_status",
                        "affected_orders", "surviving_route_count",
                        "blocked_pct"
                    ]].sort_values("affected_orders", ascending=False).copy()
                    df_rr_disp.columns = [
                        "Origin", "Destination", "Status",
                        "Orders", "Alt Routes", "Blocked Routes %"
                    ]

                    n_stranded = (df_reroute["shock_status"] == "fully_blocked").sum()
                    if n_stranded > 0:
                        st.markdown(
                            f'<div style="color:#EF4444;font-family:\'IBM Plex Mono\',monospace;'
                            f'font-size:0.75rem;margin-bottom:0.5rem">'
                            f'⚠ {n_stranded} lane{"s" if n_stranded>1 else ""} with no alternative</div>',
                            unsafe_allow_html=True,
                        )

                    st.dataframe(
                        df_rr_disp, hide_index=True, width='stretch',
                        column_config={
                            "Blocked Routes %": st.column_config.ProgressColumn(
                                "Blocked Routes %", min_value=0, max_value=100, format="%.1f%%"),
                        }
                    )

            # Penalty estimate
            if not df_penalty.empty:
                st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">Penalty estimate — cost & delay per observed rerouting</div>',
                            unsafe_allow_html=True)

                # Filters
                f1, f2, f3 = st.columns(3)
                with f1:
                    origin_options = ["All"] + sorted(df_penalty["origin"].unique().tolist())
                    pen_origin = st.selectbox("Origin", origin_options, key="pen_origin")
                with f2:
                    dest_options = ["All"] + sorted(df_penalty["destination"].unique().tolist())
                    pen_dest = st.selectbox("Destination", dest_options, key="pen_dest")
                with f3:
                    route_options = ["All"] + sorted(df_penalty["blocked_route"].unique().tolist())
                    pen_route = st.selectbox("Blocked Route", route_options, key="pen_route")

                # Apply filters
                df_pen_filtered = df_penalty.copy()
                if pen_origin != "All":
                    df_pen_filtered = df_pen_filtered[df_pen_filtered["origin"] == pen_origin]
                if pen_dest != "All":
                    df_pen_filtered = df_pen_filtered[df_pen_filtered["destination"] == pen_dest]
                if pen_route != "All":
                    df_pen_filtered = df_pen_filtered[df_pen_filtered["blocked_route"] == pen_route]

                # Alert coherent with current filter
                n_no_alt = (df_pen_filtered["rerouting_feasibility"] == "no_observed_alternative").sum()
                if n_no_alt > 0:
                    st.markdown(f"""
                    <div class="callout-critical">
                        <strong>⚠ {n_no_alt} lane{"s" if n_no_alt>1 else ""} with no observed alternative</strong><br>
                        No orders history exists for alternative routes on
                        {'these lanes' if n_no_alt>1 else 'this lane'}.
                        The real penalty would be unknown until a new route is activated.
                    </div>""", unsafe_allow_html=True)

                if df_pen_filtered.empty:
                    st.info("No lanes match the selected filters.")
                else:
                    df_pen_disp = df_pen_filtered[[
                        "origin", "destination", "blocked_route", "affected_orders",
                        "rerouting_feasibility", "alternative_route",
                        "est_cost_delta_usd", "est_lead_delta_days"
                    ]].copy()

                    df_pen_disp["rerouting_feasibility"] = df_pen_disp["rerouting_feasibility"].replace({
                        "no_observed_alternative": "No observed alternative",
                        "reroutable_from_history": "Reroutable"
                    })
                    df_pen_disp.columns = [
                        "Origin", "Destination", "Blocked Route",
                        "Orders", "Feasibility", "Alternative Route",
                        "Cost Δ (USD)", "Lead Time Δ (d)"
                    ]
                    
                    st.caption("Tip: you can sort directly in the table by clicking on column headers.")

                    st.dataframe(
                        df_pen_disp.sort_values("Orders", ascending=False),
                        hide_index=True, width='stretch',
                        column_config={
                            "Orders": st.column_config.NumberColumn("Orders", format="%d"),
                            "Cost Δ (USD)": st.column_config.NumberColumn("Cost Δ ($)", format="%.2f"),
                        }
                    )
                    st.caption(
                        "Cost Δ and Lead Time Δ based on observed alternative orders history. "
                        "Positive values = rerouting is more expensive/slower than the original route."
                    )

    elif run_route and not blocked_routes:
        st.info("Please select one or more routes to simulate a blockade.")



# SECTION 2 - Node Failure

with tab_node:
    render_section_header("Node Failure Simulation")

    if what_if_db_unavailable and what_if_db_unavailable_tab == "node":
        _show_neo4j_unavailable_warning()

    # Presets
    st.markdown('<div class="preset-label">Quick Presets</div>', unsafe_allow_html=True)
    np_c1, np_c2, np_c3 = st.columns(3)
    preset_cities = None
    with np_c1:
        if st.button("Shanghai",                width='stretch'): preset_cities = ["Shanghai"]
    with np_c2:
        if st.button("Shanghai + Santos",       width='stretch'): preset_cities = ["Shanghai", "Santos"]
    with np_c3:
        if st.button("Shanghai + Rotterdam",    width='stretch'): preset_cities = ['Shanghai', 'Rotterdam']

    if preset_cities is not None:
        st.session_state["blocked_cities"] = preset_cities
        st.rerun()

    default_cities = st.session_state.get("blocked_cities", ["Shanghai"])
    blocked_cities = st.multiselect(
        "Blocked cities",
        options=ALL_CITIES,
        default=default_cities,
    )

    run_node = st.button(
        "▶ Run Node Failure",
        type="primary",
        key="run_node",
    )

    # Only query and store results when button is pressed
    if run_node:
        if not blocked_cities:
            st.session_state["node_results"] = None
            st.session_state["node_blocked"] = []
        else:
            with st.spinner("Simulating node failure..."):
                try:
                    df_local       = Block6Queries.node_failure_local_impact(driver, blocked_cities)
                    df_substitute  = Block6Queries.node_failure_lane_substitution(driver, blocked_cities)
                    st.session_state["what_if_db_unavailable"] = False
                    st.session_state["what_if_db_unavailable_tab"] = None
                    st.session_state["node_results"] = (df_local, df_substitute)
                    st.session_state["node_blocked"] = blocked_cities
                except Exception as exc:
                    if _is_neo4j_connection_error(exc):
                        st.session_state["what_if_db_unavailable"] = True
                        st.session_state["what_if_db_unavailable_tab"] = "node"
                        _show_neo4j_unavailable_warning()
                    else:
                        st.warning(
                            "Node failure simulation is temporarily unavailable. "
                            "Please try again."
                        )

    # Render stored results (only if they exist)
    if st.session_state.get("node_results") is not None:
        df_local, df_substitute = st.session_state["node_results"]
        displayed_cities = st.session_state.get("node_blocked", blocked_cities)

        if df_local.empty:
            st.info("The selected blockade does not affect any active orders.")

        # Critical hub callout
        critical_blocked = [c for c in displayed_cities if c in CRITICAL_HUBS]
        if critical_blocked:
            st.markdown(f"""
            <div class="callout-critical">
                <strong>⚠ Critical hub affected — {', '.join(critical_blocked)}</strong><br>
                {'This city is' if len(critical_blocked)==1 else 'These cities are'}
                a structural node of the network. Its failure can trigger cascading effects
                across multiple lanes and logistics communities.
            </div>""", unsafe_allow_html=True)

        # KPI cards
        if not df_local.empty:
            st.markdown('<div class="section-label">Local impact per city — directly incident flows</div>',
                        unsafe_allow_html=True)
            city_cols = st.columns(len(df_local))
            for i, (_, row) in enumerate(df_local.iterrows()):
                total = int(row["total_affected_orders"])
                with city_cols[i]:
                    st.markdown(f"""
                    <div class="impact-card" style="border-left-color:#EF4444">
                        <div class="ic-label">🏙 {row['blocked_city']}</div>
                        <div class="ic-value" style="color:#EF4444">{total:,}</div>
                        <div class="ic-sub">affected orders</div>
                    </div>
                    <div class="impact-card" style="border-left-color:#F59E0B;margin-top:0">
                        <div class="ic-label">Outbound</div>
                        <div class="ic-value" style="font-size:1.1rem">
                            {int(row['outbound_orders']):,}
                            <span style="font-size:0.75rem;color:#6B7280">
                                · {int(row['outbound_lanes'])} lanes
                            </span>
                        </div>
                    </div>
                    <div class="impact-card" style="border-left-color:#3B82F6;margin-top:0">
                        <div class="ic-label">Inbound</div>
                        <div class="ic-value" style="font-size:1.1rem">
                            {int(row['inbound_orders']):,}
                            <span style="font-size:0.75rem;color:#6B7280">
                                · {int(row['inbound_lanes'])} lanes
                            </span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # Substitute lanes — by product
        if df_substitute is not None and not df_substitute.empty:
            st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
            st.markdown('<div class="section-label">Substitute lanes — by product</div>',
                        unsafe_allow_html=True)
            st.markdown(
                "For each severed lane and product, candidate cities that already have observed history "
                "shipping or receiving the same product to/from the surviving endpoint. "
                "Cost and lead-time deltas are computed against the failed lane's averages.",
                unsafe_allow_html=True,
            )

            # Filters
            sf1, sf2, sf3, sf4 = st.columns(4)
            with sf1:
                failed_options = ["All"] + sorted(df_substitute["failed_city"].unique().tolist())
                sub_failed = st.selectbox("Failed city", failed_options, key="sub_failed")
            with sf2:
                surv_options = ["All"] + sorted(df_substitute["surviving_city"].unique().tolist())
                sub_surv = st.selectbox("Surviving endpoint", surv_options, key="sub_surv")
            with sf3:
                prod_options = ["All"] + sorted(df_substitute["product"].unique().tolist())
                sub_prod = st.selectbox("Product", prod_options, key="sub_prod")
            with sf4:
                feas_options = ["All", "Reroutable", "No observed alternative"]
                sub_feas = st.selectbox("Feasibility", feas_options, key="sub_feas")

            df_sub_filtered = df_substitute.copy()
            if sub_failed != "All":
                df_sub_filtered = df_sub_filtered[df_sub_filtered["failed_city"] == sub_failed]
            if sub_surv != "All":
                df_sub_filtered = df_sub_filtered[df_sub_filtered["surviving_city"] == sub_surv]
            if sub_prod != "All":
                df_sub_filtered = df_sub_filtered[df_sub_filtered["product"] == sub_prod]
            if sub_feas == "Reroutable":
                df_sub_filtered = df_sub_filtered[df_sub_filtered["feasibility"] == "reroutable_from_history"]
            elif sub_feas == "No observed alternative":
                df_sub_filtered = df_sub_filtered[df_sub_filtered["feasibility"] == "no_observed_alternative"]

            # Alert: how many (lane, product) pairs have no alternative?
            no_alt_pairs = (
                df_sub_filtered[df_sub_filtered["feasibility"] == "no_observed_alternative"]
                [["failed_city", "surviving_city", "product"]]
                .drop_duplicates()
            )
            if len(no_alt_pairs) > 0:
                st.markdown(f"""
                <div class="callout-critical">
                    <strong>⚠ {len(no_alt_pairs)} (lane × product) pair{"s" if len(no_alt_pairs) > 1 else ""}
                    with no observed alternative</strong><br>
                    No order history exists for any city shipping the same product to/from the surviving endpoint.
                    The real cost of substitution is unknown until a new lane is activated.
                </div>""", unsafe_allow_html=True)

            if df_sub_filtered.empty:
                st.info("No rows match the selected filters.")
            else:
                # Build a friendly lane label using failed_role to keep direction correct.
                def _lane_label(r):
                    if r["failed_role"] == "origin":
                        return f"{r['failed_city']} → {r['surviving_city']}"
                    return f"{r['surviving_city']} → {r['failed_city']}"

                def _sub_lane_label(r):
                    if r["substitute_city"] is None or (isinstance(r["substitute_city"], float) and pd.isna(r["substitute_city"])):
                        return "—"
                    if r["failed_role"] == "origin":
                        return f"{r['substitute_city']} → {r['surviving_city']}"
                    return f"{r['surviving_city']} → {r['substitute_city']}"

                df_disp = df_sub_filtered.copy()
                df_disp["Severed lane"] = df_disp.apply(_lane_label, axis=1)
                df_disp["Substitute lane"] = df_disp.apply(_sub_lane_label, axis=1)
                df_disp["Feasibility"] = df_disp["feasibility"].replace({
                    "reroutable_from_history": "Reroutable",
                    "no_observed_alternative": "No observed alternative",
                })

                df_disp = df_disp[[
                    "Severed lane", "product", "affected_orders",
                    "Substitute lane", "sub_history_orders",
                    "cost_delta_usd", "lead_delta_days", "Feasibility",
                ]].rename(columns={
                    "product":             "Product",
                    "affected_orders":     "Affected orders",
                    "sub_history_orders":  "Substitute history",
                    "cost_delta_usd":      "Cost Δ (USD)",
                    "lead_delta_days":     "Lead Time Δ (d)",
                })

                df_disp = df_disp.sort_values(
                    by=["Affected orders", "Severed lane", "Product"],
                    ascending=[False, True, True],
                )

                st.dataframe(
                    df_disp, hide_index=True, width='stretch',
                    column_config={
                        "Affected orders":    st.column_config.NumberColumn(format="%d"),
                        "Substitute history": st.column_config.NumberColumn(format="%d"),
                        "Cost Δ (USD)":       st.column_config.NumberColumn(format="%.2f"),
                        "Lead Time Δ (d)":    st.column_config.NumberColumn(format="%.2f"),
                    },
                )
                st.caption(
                    "Cost Δ and Lead Time Δ are computed from observed orders on the substitute lane. "
                    "Positive values = substitute is more expensive / slower than the failed lane."
                )

    elif run_node and not blocked_cities:
        st.info("Please select one or more cities to simulate a blockade.")



# SECTION 3 - Path Optimization

with tab_path:
    render_section_header("Emergency Path Optimization")

    if what_if_db_unavailable and what_if_db_unavailable_tab == "path":
        _show_neo4j_unavailable_warning()

    st.markdown(
        "Find the best route between two cities — by lead time, cost or risk. "
        "All three criteria are compared side by side."
    )

    # Controls
    pc1, pc2 = st.columns(2)
    with pc1:
        src_city = st.selectbox("Origin", options=SOURCE_CITIES, index=SOURCE_CITIES.index("Shanghai"))
    with pc2:
        tgt_city = st.selectbox("Destination", options=TARGET_CITIES, index=TARGET_CITIES.index("Rotterdam"))

    run_path = st.button(
        "▶ Find Optimal Paths",
        type="primary",
        key="run_path",
    )

    # Only query and store results when button is pressed
    if run_path:
        if src_city == tgt_city:
            st.session_state["path_results"] = None
        else:
            weight_configs = [
                ("avg_lead_time_days",      "#3B82F6", "Minimum Lead Time", "days"),
                ("avg_cost_usd",            "#10B981", "Minimum Cost",      "USD"),
                ("avg_combined_risk_score", "#EF4444", "Minimum Risk",      "score"),
            ]
            results = {}
            with st.spinner("Running Dijkstra for 3 criteria..."):
                for weight, _, _, _ in weight_configs:
                    try:
                        df_p = Block6Queries.shortest_path_by_weight(
                            driver, src_city, tgt_city, weight
                        )
                        results[weight] = df_p
                    except Exception as exc:
                        if _is_neo4j_connection_error(exc):
                            st.session_state["what_if_db_unavailable"] = True
                            st.session_state["what_if_db_unavailable_tab"] = "path"
                            _show_neo4j_unavailable_warning()
                            results = None
                            break
                        results[weight] = pd.DataFrame()

            if results is not None:
                st.session_state["what_if_db_unavailable"] = False
                st.session_state["what_if_db_unavailable_tab"] = None
                st.session_state["path_results"] = results
                st.session_state["path_src"] = src_city
                st.session_state["path_tgt"] = tgt_city

    # Render stored results (only if they exist)
    if st.session_state.get("path_results") is not None:
        results = st.session_state["path_results"]

        weight_configs = [
            ("avg_lead_time_days",      "#3B82F6", "Minimum Lead Time", "days"),
            ("avg_cost_usd",            "#10B981", "Minimum Cost",      "USD"),
            ("avg_combined_risk_score", "#EF4444", "Minimum Risk",      "score"),
        ]

        st.markdown("")
        st.markdown('<div class="section-label">Optimal path comparison by criterion</div>',
                    unsafe_allow_html=True)

        path_cols = st.columns(3)
        for col, (weight, color, title, unit) in zip(path_cols, weight_configs):
            with col:
                df_p = results.get(weight, pd.DataFrame())
                st.markdown(
                    f'<div class="path-weight-label" style="color:{color}">{title}</div>',
                    unsafe_allow_html=True,
                )
                if df_p.empty:
                    st.markdown(
                        '<div style="color:#6B7280;font-size:0.82rem">'
                        'No path found between these two nodes.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    row = df_p.iloc[0]
                    cities = row["path_cities"]
                    total  = row["total_path_cost"]
                    costs  = row.get("accumulated_costs", [])

                    # Path visualization
                    path_html = ""
                    for j, city in enumerate(cities):
                        path_html += f'<span class="path-node">{city}</span>'
                        if j < len(cities) - 1:
                            seg_cost = ""
                            if len(costs) > j + 1:
                                delta = costs[j + 1] - costs[j]
                                if weight == "avg_combined_risk_score":
                                    seg_cost = (
                                        f'<span style="font-size:0.65rem;color:#6B7280;'
                                        f'font-family:\'IBM Plex Mono\',monospace"> '
                                        f'x{delta:.2f}</span>'
                                    )
                                else:
                                    seg_cost = (
                                        f'<span style="font-size:0.65rem;color:#6B7280;'
                                        f'font-family:\'IBM Plex Mono\',monospace"> '
                                        f'+{delta:.2f}</span>'
                                    )
                            path_html += f'<span class="path-arrow">→{seg_cost}</span>'

                    st.markdown(f'<div class="path-row">{path_html}</div>', unsafe_allow_html=True)

                    # Total cost badge
                    st.markdown(
                        f'<div style="background:#1A1D27;border:1px solid #2A2D3A;'
                        f'border-left:3px solid {color};border-radius:6px;'
                        f'padding:0.5rem 0.8rem;margin-top:0.4rem">'
                        f'<span style="font-family:\'IBM Plex Mono\',monospace;'
                        f'font-size:0.6rem;color:#6B7280;text-transform:uppercase;'
                        f'letter-spacing:0.1em">Total {WEIGHT_LABELS[weight]}</span><br>'
                        f'<span style="font-size:1.2rem;font-weight:700;color:{color};'
                        f'font-family:\'IBM Plex Sans\',sans-serif">'
                        f'{total:.2f} {unit}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # Hop count
                    hops = len(cities) - 1
                    st.markdown(
                        f'<div style="font-family:\'IBM Plex Mono\',monospace;'
                        f'font-size:0.65rem;color:#6B7280;margin-top:0.3rem">'
                        f'{hops} hop{"s" if hops!=1 else ""} · '
                        f'{" → ".join(cities)}</div>',
                        unsafe_allow_html=True,
                    )

        # Comparison summary table
        st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Comparative summary</div>', unsafe_allow_html=True)

        summary_rows = []
        for weight, color, title, unit in weight_configs:
            df_p = results.get(weight, pd.DataFrame())
            if not df_p.empty:
                row = df_p.iloc[0]
                summary_rows.append({
                    "Criterion": title,
                    "Path":      " → ".join(row["path_cities"]),
                    "Total":     f"{row['total_path_cost']:.2f} {unit}",
                    "Hops":      len(row["path_cities"]) - 1,
                })

        if summary_rows:
            st.dataframe(
                pd.DataFrame(summary_rows),
                hide_index=True,
                width='stretch',
            )
            st.caption(
                "Each row represents the optimal path for a different criterion. "
                "Compare hops and total cost to choose the best alternative for your scenario."
            )

    elif run_path and src_city == tgt_city:
        st.warning("Origin and destination must be different cities.")