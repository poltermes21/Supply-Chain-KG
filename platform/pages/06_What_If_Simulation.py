import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from connection import get_neo4j_driver
from analysis.queriesv2.block6_what_if import Block6Queries

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="What-If Scenarios", layout="wide")

# ─────────────────────────────────────────────
# SHARED STYLE
# ─────────────────────────────────────────────
FONT_SANS   = "IBM Plex Sans, sans-serif"
FONT_MONO   = "IBM Plex Mono, monospace"
GRID_COLOR  = "#2A2D3A"
AXIS_COLOR  = "#6B7280"
TEXT_COLOR  = "#E5E7EB"
TRANSPARENT = "rgba(0,0,0,0)"

SHOCK_COLORS = {
    "stranded":         "#EF4444",
    "needs_rerouting":  "#F59E0B",
    "partially_hedged": "#10B981",
}

WEIGHT_LABELS = {
    "avg_lead_time_days":      "Lead Time (dies)",
    "avg_cost_usd":            "Cost (USD)",
    "avg_combined_risk_score": "Risk Score",
}

ALL_ROUTES = ["Suez", "Pacific", "Intra-Asia", "Atlantic", "CoGH"]
ALL_CITIES = ["Shanghai", "Rotterdam", "Shenzhen", "Mumbai", "Hamburg",
              "Tokyo", "Santos", "Singapore", "Felixstowe",
              "New York", "Los Angeles"]
CRITICAL_HUBS = {"Shanghai", "Rotterdam", "Singapore"}

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

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">Block 6</div>', unsafe_allow_html=True)
st.markdown("# 🧪 What-If Scenario Simulation")
st.markdown(
    "Simulate network shocks — route blockages, hub failures and path optimization — "
    "to quantify resilience and identify rerouting alternatives."
)
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

driver = get_neo4j_driver()

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab_route, tab_node, tab_path = st.tabs([
    "🛣️  Route Shock",
    "🏙️  Node Failure",
    "🔍  Path Optimization",
])


# ═══════════════════════════════════════════════
# TAB 1 — ROUTE SHOCK
# ═══════════════════════════════════════════════
with tab_route:
    st.markdown('<div class="section-title">Route Shock Simulation</div>', unsafe_allow_html=True)

    # — Presets —
    st.markdown('<div class="preset-label">Presets ràpids</div>', unsafe_allow_html=True)
    pre_c1, pre_c2, pre_c3, pre_c4 = st.columns(4)
    preset_route = None
    with pre_c1:
        if st.button("🔴 Suez Blockage", use_container_width=True):
            preset_route = ["Suez"]
    with pre_c2:
        if st.button("🟠 Suez + Intra-Asia", use_container_width=True):
            preset_route = ["Suez", "Intra-Asia"]
    with pre_c3:
        if st.button("🟡 Pacific + Atlantic", use_container_width=True):
            preset_route = ["Pacific", "Atlantic"]
    with pre_c4:
        if st.button("⚫ All routes", use_container_width=True):
            preset_route = ALL_ROUTES

    if preset_route is not None:
        st.session_state["blocked_routes"] = preset_route

    default_routes = st.session_state.get("blocked_routes", ["Suez"])
    blocked_routes = st.multiselect(
        "Rutes bloquejades",
        options=ALL_ROUTES,
        default=default_routes,
    )

    run_route = st.button("▶ Run Route Shock", type="primary", use_container_width=False)

    if run_route or st.session_state.get("route_ran", False):
        st.session_state["route_ran"] = True

        with st.spinner("Simulating route shock..."):
            df_overview   = Block6Queries.route_shock_overview(driver, blocked_routes)
            df_reroute    = Block6Queries.route_shock_reroutability(driver, blocked_routes)
            df_penalty    = Block6Queries.route_shock_penalty_estimate(driver, blocked_routes)

        if df_overview.empty:
            st.info("Cap enviament afectat per les rutes seleccionades.")
        else:
            ov = df_overview.iloc[0]

            # — Callout —
            pct = float(ov["pct_total_network"])
            if pct >= 30:
                st.markdown(f"""
                <div class="callout-critical">
                    <strong>⚠ Impacte crític — {pct:.1f}% de la xarxa afectada</strong><br>
                    El bloqueig de <strong>{', '.join(blocked_routes)}</strong> afectaria
                    <strong>{int(ov['affected_shipments']):,} enviaments</strong>.
                    Aquesta és una disrupció de primer ordre que requereix activació immediata de rutes alternatives.
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="callout-warn">
                    <strong>⚠ Impacte moderat — {pct:.1f}% de la xarxa afectada</strong><br>
                    El bloqueig de <strong>{', '.join(blocked_routes)}</strong> afectaria
                    <strong>{int(ov['affected_shipments']):,} enviaments</strong>.
                </div>""", unsafe_allow_html=True)

            # — KPI cards —
            k1, k2, k3, k4 = st.columns(4)
            kpi_data = [
                (k1, "Enviaments afectats",  f"{int(ov['affected_shipments']):,}", "#EF4444",
                 "sobre el total de la xarxa"),
                (k2, "% Xarxa exposada",     f"{pct:.1f}%",                        "#F59E0B",
                 "del volum total"),
                (k3, "Avg Lead Time",         f"{ov['avg_lead_time_days']:.1f}d",   "#6B7280",
                 "de les lanes afectades"),
                (k4, "Disruption rate actual",f"{ov['current_disruption_rate_pct']:.1f}%","#6B7280",
                 "en condicions normals"),
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

            # — Reroutability Sankey + stranded table —
            if not df_reroute.empty:
                col_san, col_strand = st.columns([3, 2])
                
                def hex_to_rgba(hex_color: str, alpha: float = 0.53) -> str:
                    hex_color = hex_color.lstrip("#")
                    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
                    return f"rgba({r},{g},{b},{alpha})"

                with col_san:
                    st.markdown('<div class="section-label">Reroutability — Sankey per shock status</div>',
                                unsafe_allow_html=True)

                    # Aggregate: from shock_status → origin → destination
                    # Nodes: status nodes + city nodes
                    status_nodes = list(SHOCK_COLORS.keys())
                    city_nodes   = sorted(
                        set(df_reroute["origin"].tolist()) | set(df_reroute["destination"].tolist())
                    )
                    all_nodes  = status_nodes + city_nodes
                    node_map   = {n: i for i, n in enumerate(all_nodes)}
                    node_colors = (
                        [SHOCK_COLORS[s] for s in status_nodes] +
                        ["#3B82F6"] * len(city_nodes)
                    )

                    # Edges: status → origin
                    agg_status_origin = (
                        df_reroute.groupby(["shock_status", "origin"])["affected_shipments"]
                        .sum().reset_index()
                    )
                    # Edges: origin → destination
                    agg_od = df_reroute[["origin", "destination", "affected_shipments"]].copy()

                    sources, targets, values, colors_link = [], [], [], []
                    for _, r in agg_status_origin.iterrows():
                        sources.append(node_map[r["shock_status"]])
                        targets.append(node_map[r["origin"]])
                        values.append(int(r["affected_shipments"]))
                        colors_link.append(hex_to_rgba(SHOCK_COLORS.get(r["shock_status"], "#6B7280")))


                    for _, r in agg_od.iterrows():
                        sources.append(node_map[r["origin"]])
                        targets.append(node_map[r["destination"]])
                        values.append(int(r["affected_shipments"]))
                        colors_link.append(hex_to_rgba("#3B82F6"))

                    fig_sankey = go.Figure(go.Sankey(
                        arrangement="snap",
                        node=dict(
                            pad=16, thickness=20,
                            label=all_nodes,
                            color=node_colors,
                            line=dict(color="#0F1117", width=0.5),
                        ),
                        link=dict(
                            source=sources, target=targets,
                            value=values, color=colors_link,
                        ),
                    ))
                    fig_sankey.update_layout(
                        **base_layout(height=380),
                        margin=dict(l=12, r=12, t=16, b=12),
                    )
                    st.plotly_chart(fig_sankey, use_container_width=True)
                    st.caption(
                        "🔴 Stranded = sense cap ruta alternativa. "
                        "🟠 Needs rerouting = ruta principal bloquejada però té alternatives. "
                        "🟢 Partially hedged = ruta alternativa ja activa."
                    )

                with col_strand:
                    st.markdown('<div class="section-label">Lanes per shock status</div>',
                                unsafe_allow_html=True)

                    status_filter = st.selectbox(
                        "Filtra per status",
                        options=["Tots"] + list(SHOCK_COLORS.keys()),
                        index=0,
                        key="status_filter",
                    )
                    df_rr_disp = df_reroute.copy()
                    if status_filter != "Tots":
                        df_rr_disp = df_rr_disp[df_rr_disp["shock_status"] == status_filter]

                    df_rr_disp = df_rr_disp[[
                        "origin", "destination", "shock_status",
                        "affected_shipments", "surviving_route_count",
                        "primary_route_share_pct"
                    ]].sort_values("affected_shipments", ascending=False).copy()
                    df_rr_disp.columns = [
                        "Origin", "Destination", "Status",
                        "Shipments", "Alt Routes", "Primary Share %"
                    ]

                    n_stranded = (df_reroute["shock_status"] == "stranded").sum()
                    if n_stranded > 0:
                        st.markdown(
                            f'<div style="color:#EF4444;font-family:\'IBM Plex Mono\',monospace;'
                            f'font-size:0.75rem;margin-bottom:0.5rem">'
                            f'⚠ {n_stranded} lane{"s" if n_stranded>1 else ""} sense alternativa</div>',
                            unsafe_allow_html=True,
                        )

                    st.dataframe(
                        df_rr_disp, hide_index=True, use_container_width=True,
                        column_config={
                            "Primary Share %": st.column_config.ProgressColumn(
                                "Primary %", min_value=0, max_value=100, format="%.1f%%"),
                        }
                    )

            # — Penalty estimate —
            if not df_penalty.empty:
                st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">Penalty estimate — cost i delay per rerouting observat</div>',
                            unsafe_allow_html=True)

                n_no_alt = (df_penalty["rerouting_feasibility"] == "no_observed_alternative").sum()
                if n_no_alt > 0:
                    st.markdown(f"""
                    <div class="callout-critical">
                        <strong>⚠ {n_no_alt} lane{"s" if n_no_alt>1 else ""} sense alternativa observada</strong><br>
                        No existeix historial d'enviaments per rutes alternatives en
                        {'aquestes lanes' if n_no_alt>1 else 'aquesta lane'}.
                        La penalització real seria desconeguda fins a l'activació d'una nova ruta.
                    </div>""", unsafe_allow_html=True)

                df_pen_disp = df_penalty[[
                    "origin", "destination", "affected_shipments",
                    "rerouting_feasibility", "observed_alt_route_count",
                    "est_cost_delta_usd", "est_lead_delta_days"
                ]].copy()
                df_pen_disp.columns = [
                    "Origin", "Destination", "Shipments",
                    "Feasibility", "Alt Routes",
                    "Cost Δ (USD)", "Lead Time Δ (d)"
                ]

                def feasibility_style(val):
                    if val == "no_observed_alternative":
                        return "color:#EF4444;font-weight:600"
                    return "color:#10B981;font-weight:600"

                st.dataframe(
                    df_pen_disp.sort_values("Shipments", ascending=False),
                    hide_index=True, use_container_width=True,
                    column_config={
                        "Shipments": st.column_config.NumberColumn("Shipments", format="%d"),
                        "Cost Δ (USD)": st.column_config.NumberColumn("Cost Δ ($)", format="%.2f"),
                    }
                )
                st.caption(
                    "Cost Δ i Lead Time Δ basats en l'historial d'enviaments alternatius observats. "
                    "Valors positius = rerouting és més car/lent que la ruta original."
                )


# ═══════════════════════════════════════════════
# TAB 2 — NODE FAILURE
# ═══════════════════════════════════════════════
with tab_node:
    st.markdown('<div class="section-title">Node Failure Simulation</div>', unsafe_allow_html=True)

    # Presets
    st.markdown('<div class="preset-label">Presets ràpids</div>', unsafe_allow_html=True)
    np_c1, np_c2, np_c3 = st.columns(3)
    preset_cities = None
    with np_c1:
        if st.button("🔴 Shanghai",           use_container_width=True): preset_cities = ["Shanghai"]
    with np_c2:
        if st.button("🟠 Shanghai + Santos",   use_container_width=True): preset_cities = ["Shanghai", "Santos"]
    with np_c3:
        if st.button("⚫ All hubs",            use_container_width=True): preset_cities = list(CRITICAL_HUBS)

    if preset_cities is not None:
        st.session_state["blocked_cities"] = preset_cities

    default_cities = st.session_state.get("blocked_cities", ["Shanghai"])
    blocked_cities = st.multiselect(
        "Ciutats bloquejades",
        options=ALL_CITIES,
        default=default_cities,
    )

    run_node = st.button("▶ Run Node Failure", type="primary", key="run_node")

    if run_node or st.session_state.get("node_ran", False):
        st.session_state["node_ran"] = True

        with st.spinner("Simulating node failure..."):
            df_local  = Block6Queries.node_failure_local_impact(driver, blocked_cities)
            df_global = Block6Queries.node_failure_global_impact(driver, blocked_cities)

        # Critical hub callout
        critical_blocked = [c for c in blocked_cities if c in CRITICAL_HUBS]
        if critical_blocked:
            st.markdown(f"""
            <div class="callout-critical">
                <strong>⚠ Hub crític afectat — {', '.join(critical_blocked)}</strong><br>
                {'Aquesta ciutat és' if len(critical_blocked)==1 else 'Aquestes ciutats són'}
                un node estructural de la xarxa. La seva fallada pot desencadenar efectes en cascada
                en múltiples lanes i comunitats logístiques.
            </div>""", unsafe_allow_html=True)

        # Local impact KPI cards
        if not df_local.empty:
            st.markdown('<div class="section-label">Impacte local per ciutat — fluxos directament incidents</div>',
                        unsafe_allow_html=True)
            city_cols = st.columns(len(df_local))
            for i, (_, row) in enumerate(df_local.iterrows()):
                total = int(row["total_affected_shipments"])
                with city_cols[i]:
                    st.markdown(f"""
                    <div class="impact-card" style="border-left-color:#EF4444">
                        <div class="ic-label">🏙 {row['blocked_city']}</div>
                        <div class="ic-value" style="color:#EF4444">{total:,}</div>
                        <div class="ic-sub">enviaments afectats</div>
                    </div>
                    <div class="impact-card" style="border-left-color:#F59E0B;margin-top:0">
                        <div class="ic-label">Outbound</div>
                        <div class="ic-value" style="font-size:1.1rem">
                            {int(row['outbound_shipments']):,}
                            <span style="font-size:0.75rem;color:#6B7280">
                                · {int(row['outbound_lanes'])} lanes
                            </span>
                        </div>
                    </div>
                    <div class="impact-card" style="border-left-color:#3B82F6;margin-top:0">
                        <div class="ic-label">Inbound</div>
                        <div class="ic-value" style="font-size:1.1rem">
                            {int(row['inbound_shipments']):,}
                            <span style="font-size:0.75rem;color:#6B7280">
                                · {int(row['inbound_lanes'])} lanes
                            </span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # Global impact bar chart
        if not df_global.empty:
            st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
            st.markdown('<div class="section-label">Impacte global — lanes afectades per la fallada</div>',
                        unsafe_allow_html=True)

            df_g = df_global.copy()
            df_g["lane"] = df_g["origin"] + " → " + df_g["destination"]
            df_g = df_g.sort_values("affected_shipments", ascending=True).head(20)

            fig_node = go.Figure(go.Bar(
                x=df_g["affected_shipments"],
                y=df_g["lane"],
                orientation="h",
                marker=dict(
                    color=df_g["risk_score"],
                    colorscale="RdYlGn_r",
                    colorbar=dict(
                        title=dict(text="Risk Score",
                                   font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR)),
                        tickfont=dict(size=9, family=FONT_SANS, color=TEXT_COLOR),
                        thickness=12,
                    ),
                    showscale=True,
                ),
                text=[f"{int(v):,}  ·  {r:.3f} risk" for v, r in
                      zip(df_g["affected_shipments"], df_g["risk_score"])],
                textposition="outside",
                textfont=dict(size=9, family=FONT_MONO, color=TEXT_COLOR),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Affected: %{x:,}<br>"
                    "Risk score: %{customdata[0]:.4f}<br>"
                    "Avg cost: $%{customdata[1]:,.0f}<br>"
                    "Avg LT: %{customdata[2]:.1f}d"
                    "<extra></extra>"
                ),
                customdata=df_g[["risk_score", "avg_cost", "avg_lead_time"]].values,
            ))
            fig_node.update_layout(
                **base_layout(height=max(320, len(df_g) * 34 + 60)),
                xaxis=styled_xaxis(title="Enviaments afectats"),
                yaxis=styled_yaxis(showgrid=False),
                margin=dict(l=12, r=160, t=16, b=12),
            )
            st.plotly_chart(fig_node, use_container_width=True)
            st.caption(
                "Top 20 lanes per volum afectat. Color = risk score de la lane (vermell = major risc). "
                "Inclou totes les lanes on la ciutat fallada és origen o destí."
            )


# ═══════════════════════════════════════════════
# TAB 3 — PATH OPTIMIZATION
# ═══════════════════════════════════════════════
with tab_path:
    st.markdown('<div class="section-title">Emergency Path Optimization</div>', unsafe_allow_html=True)
    st.markdown(
        "Troba el camí òptim entre dos nodes de la xarxa via Dijkstra sobre el graf `CITY_FLOW`. "
        "Compara els 3 criteris d'optimització en paral·lel."
    )

    # Controls
    pc1, pc2 = st.columns(2)
    with pc1:
        src_city = st.selectbox("Origen", options=ALL_CITIES, index=ALL_CITIES.index("Shanghai"))
    with pc2:
        tgt_city = st.selectbox("Destí",  options=ALL_CITIES, index=ALL_CITIES.index("Rotterdam")
                                if "Rotterdam" in ALL_CITIES else 0)

    run_path = st.button("▶ Find Optimal Paths", type="primary", key="run_path")

    if run_path or st.session_state.get("path_ran", False):
        st.session_state["path_ran"] = True

        if src_city == tgt_city:
            st.warning("Origen i destí han de ser ciutats diferents.")
        else:
            weight_configs = [
                ("avg_lead_time_days",      "#3B82F6", "🕐 Mínim Lead Time",   "dies"),
                ("avg_cost_usd",            "#10B981", "💰 Mínim Cost",        "USD"),
                ("avg_combined_risk_score", "#EF4444", "🛡 Mínim Risc",        "score"),
            ]

            results = {}
            with st.spinner("Running Dijkstra for 3 criteria..."):
                for weight, _, _, _ in weight_configs:
                    try:
                        df_p = Block6Queries.shortest_path_by_weight(
                            driver, src_city, tgt_city, weight
                        )
                        results[weight] = df_p
                    except Exception as e:
                        results[weight] = pd.DataFrame()

            st.markdown("")
            st.markdown('<div class="section-label">Comparativa de camins òptims per criteri</div>',
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
                            'Cap camí trobat entre aquests dos nodes.</div>',
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
            st.markdown('<div class="section-label">Resum comparatiu</div>', unsafe_allow_html=True)

            summary_rows = []
            for weight, color, title, unit in weight_configs:
                df_p = results.get(weight, pd.DataFrame())
                if not df_p.empty:
                    row = df_p.iloc[0]
                    summary_rows.append({
                        "Criteri":      title,
                        "Camí":         " → ".join(row["path_cities"]),
                        "Total":        f"{row['total_path_cost']:.2f} {unit}",
                        "Hops":         len(row["path_cities"]) - 1,
                    })

            if summary_rows:
                st.dataframe(
                    pd.DataFrame(summary_rows),
                    hide_index=True,
                    use_container_width=True,
                )
                st.caption(
                    "Cada fila representa el camí òptim per un criteri diferent. "
                    "Compara hops i cost total per triar la millor alternativa per al teu escenari."
                )