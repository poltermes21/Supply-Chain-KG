import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from shared.connection import get_neo4j_driver
from analysis.queriesv2 import Block1Queries

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="Operational Baseline", layout="wide")

# ─────────────────────────────────────────────
# PLOTLY SHARED STYLE HELPERS
# ─────────────────────────────────────────────
FONT_SANS   = "IBM Plex Sans, sans-serif"
FONT_MONO   = "IBM Plex Mono, monospace"
GRID_COLOR  = "#2A2D3A"
AXIS_COLOR  = "#6B7280"
TEXT_COLOR1  = "#E5E7EB"
TEXT_COLOR2 = "#1A1D27"
TRANSPARENT = "rgba(0,0,0,0)"

ROUTE_COLORS = {
    "Suez": "#1D4ED8",
    "Pacific": "#10B981", 
    "Intra-Asia": "#F59E0B",
    "CoGH": "#EF4444",
    "Atlantic": "#8B5CF6"
}
DEFAULT_ROUTE_COLOR = "#6B7280"

def base_layout(**kwargs):
    defaults = dict(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font=dict(family=FONT_SANS, color=TEXT_COLOR1),
        hoverlabel=dict(
            bgcolor="#1A1D27",
            bordercolor="#374151",
            font=dict(family=FONT_SANS, size=12, color=TEXT_COLOR1),
        ),
    )
    defaults.update(kwargs)
    return defaults

def styled_xaxis(**kwargs):
    d = dict(
        gridcolor=GRID_COLOR,
        linecolor="#E5E7EB",
        tickfont=dict(family=FONT_SANS, size=10, color=AXIS_COLOR),
        title_font=dict(family=FONT_SANS, size=11, color=AXIS_COLOR),
        zeroline=False,
    )
    d.update(kwargs)
    return d

def styled_yaxis(**kwargs):
    d = dict(
        gridcolor=GRID_COLOR,
        linecolor="#E5E7EB",
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
section.main,
.stApp {
    background-color: #0F1117 !important;
    color: #E5E7EB !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}

[data-testid="stSidebar"] {
    background-color: #1A1D27 !important;
}

p, li, span, label, div {
    color: #E5E7EB;
    font-family: 'IBM Plex Sans', sans-serif;
}

h1, h2, h3 {
    color: #F9FAFB !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}

.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.67rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #6B7280;
    margin-bottom: 0.3rem;
}

.section-title {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.2rem;
    font-weight: 700;
    color: #F9FAFB;
    margin-bottom: 1rem;
    border-left: 3px solid #F59E0B;
    padding-left: 0.75rem;
    line-height: 1.3;
}

.kpi-card {
    background: #1A1D27;
    border: 1px solid #2A2D3A;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.4rem;
    border-left-width: 3px;
    min-height: 115px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.kpi-neutral { border-left-color: #4B5563; }
.kpi-ok      { border-left-color: #10B981; }
.kpi-alert   { border-left-color: #EF4444; }
.kpi-orange { border-left-color: #F59E0B; }
.kpi-blue   { border-left-color: #3B82F6; }

.kpi-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6B7280;
    margin-bottom: 0.2rem;
}
.kpi-value {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.55rem;
    font-weight: 700;
    color: #F9FAFB;
    line-height: 1.1;
}
.kpi-sub {
    font-size: 0.72rem;
    color: #9CA3AF;
    margin-top: 0.2rem;
}

.callout-box {
    background: #1C1A0F;
    border: 1px solid #78350F;
    border-left: 4px solid #F59E0B;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.85rem;
    color: #FCD34D;
}
.callout-box strong {
    font-family: 'IBM Plex Mono', monospace;
    color: #FCD34D;
}

.divider-line {
    border: none;
    border-top: 1px solid #2A2D3A;
    margin: 1.75rem 0;
}

[data-testid="stDataFrame"] * {
    font-family: 'IBM Plex Sans', sans-serif !important;
}

[data-testid="stSelectbox"] label {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.75rem !important;
    color: #6B7280 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">Block 1</div>', unsafe_allow_html=True)
st.markdown("# 📦 Operational Baseline")
st.markdown(
    "System-wide performance characterization under observed conditions — "
    "volume, efficiency, delay exposure and structural resilience."
)
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
driver = get_neo4j_driver()

@st.cache_data(ttl=600)
def load_block1_data():
    return Block1Queries.run_all(driver)

with st.spinner("Loading graph data..."):
    data = load_block1_data()

kpis         = data["global_baseline_kpis"].iloc[0]
df_route     = data["orders_by_route"]
df_mode      = data["orders_by_transport_mode"]
df_product   = data["orders_by_product"]
df_prod_dist = data["product_distribution"]
df_severity  = data["delay_severity_distribution"]
df_od        = data["od_redundancy_profile"]
df_temporal  = data["temporal_trend"].copy()
df_temporal["date"] = pd.to_datetime(
    df_temporal["year"].astype(str) + "-" + df_temporal["month"].astype(str) + "-01"
)

palette_prod = px.colors.qualitative.Safe


# ═══════════════════════════════════════════════
# SECTION 1 — KPIs baseline
# ═══════════════════════════════════════════════
st.markdown('<div class="section-title">1 · KPIs baseline</div>', unsafe_allow_html=True)

col_v, col_r = st.columns(2)

with col_v:
    st.markdown('<div class="section-label">Volume & Operations</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="kpi-card kpi-neutral">
            <div class="kpi-label">Total Orders</div>
            <div class="kpi-value">{int(kpis['total_orders']):,}</div>
            <div class="kpi-sub">Analyzed orders</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card kpi-neutral">
            <div class="kpi-label">Avg Lead Time</div>
            <div class="kpi-value">{kpis['avg_actual_lead_time_days']:.1f}<span style="font-size:1rem;font-weight:400;color:#9CA3AF"> d</span></div>
            <div class="kpi-sub">P95: {kpis['p95_actual_lead_time_days']:.1f} days</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        eff = kpis['avg_lead_time_deviation_pct']
        eff_class = "kpi-alert" if eff >= 0 else "kpi-ok"
        st.markdown(f"""
        <div class="kpi-card {eff_class}">
            <div class="kpi-label">LT Perfomance</div>
            <div class="kpi-value">{eff:.1f}%</div>
            <div class="kpi-sub">vs scheduled plan</div>
        </div>
        """, unsafe_allow_html=True)

with col_r:
    st.markdown('<div class="section-label">Risk & Cost</div>', unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    with c4:
        dr = kpis['delay_rate_pct']
        dr_class = "kpi-ok" if dr < 10 else "kpi-alert" if dr > 20 else "kpi-neutral"
        st.markdown(f"""
        <div class="kpi-card {dr_class}">
            <div class="kpi-label">Delay Rate</div>
            <div class="kpi-value">{dr:.1f}<span style="font-size:1rem;font-weight:400;color:#9CA3AF">%</span></div>
            <div class="kpi-sub">Disruption: {kpis['disruption_rate_pct']:.1f}%</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="kpi-card kpi-neutral">
            <div class="kpi-label">Avg Cost</div>
            <div class="kpi-value">${kpis['avg_shipping_cost_usd']:,.0f}</div>
            <div class="kpi-sub">P95: ${kpis['p95_shipping_cost_usd']:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with c6:
        st.markdown(f"""
        <div class="kpi-card kpi-neutral">
            <div class="kpi-label">Cost / kg</div>
            <div class="kpi-value">${kpis['avg_cost_per_kg']:.2f}</div>
            <div class="kpi-sub">Avg per kilogram</div>
        </div>""", unsafe_allow_html=True)

st.markdown("")

# — Temporal Perfomance —
st.markdown('<div class="section-label">Temporal Performance</div>', unsafe_allow_html=True)

metric_map = {
    "Orders": "total_orders",
    "Delay Rate (%)": "delay_rate_pct",
    "Avg Cost ($)": "avg_cost",
}

metric_label = st.selectbox(
    "Metric",
    list(metric_map.keys())
)

metric = metric_map[metric_label]

mode = st.radio(
    "Mode",
    ["Single year", "Compare years"],
    horizontal=True
)

selected_years = st.multiselect(
    "Select years",
    sorted(df_temporal["year"].unique()),
    default=sorted(df_temporal["year"].unique())[-1:] if mode == "Single year" else sorted(df_temporal["year"].unique())
)

df_plot = df_temporal[df_temporal["year"].isin(selected_years)]

fig = go.Figure()
if mode == "Single year":

    fig.add_trace(go.Scatter(
        x=df_plot["date"],
        y=df_plot[metric],
        mode="lines+markers",
        line=dict(width=3, color="#F59E0B"),
        marker=dict(size=5),
        name=str(selected_years[0])
    ))
else:
    df_plot = df_plot.sort_values(["year", "month"])

    df_plot["month_label"] = df_plot["date"].dt.strftime("%b")

    for y in sorted(df_plot["year"].unique()):
        dff = df_plot[df_plot["year"] == y]

        fig.add_trace(go.Scatter(
            x=dff["month"],
            y=dff[metric],
            mode="lines+markers",
            name=str(y),
            line=dict(width=3),
            marker=dict(size=5),
            hovertemplate=f"{y}<br>Month: %{{x}}<br>{metric_label}: %{{y:.2f}}<extra></extra>"
        ))
        
        fig.update_xaxes(
            tickmode="array",
            tickvals=list(range(1, 13)),
            ticktext=["Jan","Feb","Mar","Apr","May","Jun",
                    "Jul","Aug","Sep","Oct","Nov","Dec"]
        )
        
fig.update_layout(
    **base_layout(height=350),
    xaxis=dict(
        title="Month",
        tickformat="%b %Y",
        tickfont=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1),
    ),
    yaxis=dict(
        title=metric_label,
        gridcolor=GRID_COLOR,
        tickfont=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1),
    ),
    legend=dict(
        orientation="h",
        y=-0.2,
        font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1),
    ),
    margin=dict(l=10, r=10, t=10, b=10),
)

st.plotly_chart(fig, use_container_width=True)

# — Transport Mode side-by-side —
st.markdown('<div class="section-label">Transport Mode Split</div>', unsafe_allow_html=True)

if len(df_mode) >= 2:
    sea = df_mode[df_mode["transport_mode"].str.lower() == "sea"].iloc[0] if any(df_mode["transport_mode"].str.lower() == "sea") else None
    air = df_mode[df_mode["transport_mode"].str.lower() == "air"].iloc[0] if any(df_mode["transport_mode"].str.lower() == "air") else None

    metrics = [
        ("Volume", "pct_total", "%"),
        ("Avg Lead Time", "avg_lead_time_days", " d"),
        ("Avg Cost", "avg_cost_usd", " USD"),
        ("Delay Rate", "delay_rate_pct", "%"),
    ]
    mode_cols = st.columns(len(metrics))
    for i, (label, field, unit) in enumerate(metrics):
        with mode_cols[i]:
            sea_val = float(sea[field]) if sea is not None else 0
            air_val = float(air[field]) if air is not None else 0
            max_val = max(sea_val, air_val) if max(sea_val, air_val) > 0 else 1

            fig = go.Figure(go.Bar(
                x=["Sea", "Air"],
                y=[sea_val, air_val],
                marker_color=["#1D4ED8", "#F59E0B"],
                text=[f"{sea_val:.1f}{unit}", f"{air_val:.1f}{unit}"],
                textposition="outside",
                textfont=dict(size=11, family=FONT_MONO, color=TEXT_COLOR1),
            ))
            fig.update_layout(
                **base_layout(height=185),
                title=dict(
                    text=label,
                    font=dict(size=12, family=FONT_SANS, color="#374151"),
                    x=0, pad=dict(l=0),
                ),
                yaxis=dict(visible=False, range=[0, max_val * 1.38]),
                xaxis=dict(
                    tickfont=dict(size=11, family=FONT_SANS, color=TEXT_COLOR1),
                    linecolor="#E5E7EB",
                    showgrid=False,
                ),
                margin=dict(l=8, r=8, t=34, b=8),
            )
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════
# SECTION 2 — Traffic distribution
# ═══════════════════════════════════════════════
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
st.markdown('<div class="section-title">2 · Traffic distribution</div>', unsafe_allow_html=True)

col_left, col_right = st.columns([5, 3])

with col_left:
    st.markdown('<div class="section-label">Volume by route</div>', unsafe_allow_html=True)
    df_route_sorted = df_route.sort_values("total_orders", ascending=True)
    colors = ["#F59E0B" if "suez" in r.lower() else "#1D4ED8" for r in df_route_sorted["route"]]

    fig_route = go.Figure(go.Bar(
        x=df_route_sorted["total_orders"],
        y=df_route_sorted["route"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:,}  ({p:.1f}%)" for v, p in zip(df_route_sorted["total_orders"], df_route_sorted["pct_total"])],
        textposition="outside",
        textfont=dict(size=10, family=FONT_MONO, color=TEXT_COLOR1),
    ))
    fig_route.update_layout(
        **base_layout(height=420),
        xaxis=styled_xaxis(title="Orders", range=[0, 6100]),
        yaxis=styled_yaxis(showgrid=False),
        margin=dict(l=8, r=10, t=10, b=10),
    )
    st.plotly_chart(fig_route, use_container_width=True)

with col_right:
    st.markdown('<div class="section-label">Route profile — Lead Time, Cost & Delay (normalized)</div>', unsafe_allow_html=True)
    st.caption("Normalized values to compare relative profiles across routes.")

    cols_norm = ["avg_cost_usd", "avg_delay_days", "delay_rate_pct", "avg_lead_time_days"]
    df_radar = df_route.copy()
    for c in cols_norm:
        df_radar[c + "_norm"] = df_radar[c].rank(pct=True)

    categories = ["Avg Cost", "Avg Delay", "Delay Rate", "Lead Time"]
    fig_radar = go.Figure()
    for _, row in df_radar.iterrows():
        route_name = row["route"]
        current_color = ROUTE_COLORS.get(route_name, DEFAULT_ROUTE_COLOR)
        
        vals = [row["avg_cost_usd_norm"], row["avg_delay_days_norm"], 
                row["delay_rate_pct_norm"], row["avg_lead_time_days_norm"]]
        vals += [vals[0]]
        
        fig_radar.add_trace(go.Scatterpolar(
            r=vals,
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor=current_color,
            opacity=0.3,
            line=dict(color=current_color, width=2),
            name=route_name,
        ))
    fig_radar.update_layout(
        **base_layout(height=350),
        polar=dict(
            bgcolor=TRANSPARENT,
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                showticklabels=False,
                gridcolor="rgba(229, 231, 235, 0.3)"
            ),
            angularaxis=dict(tickfont=dict(size=11, family=FONT_SANS, color=TEXT_COLOR1)),
        ),
        legend=dict(font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1), orientation="h", y=-0.18),
        margin=dict(l=30, r=30, t=30, b=50),
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with st.expander("📋 Detailed table by route"):
    st.caption("Tip: you can sort directly in the table by clicking on column headers.")
    df_display = df_route[["route", "total_orders", "pct_total", "avg_lead_time_days", "avg_cost_usd", "avg_delay_days", "delay_rate_pct"]].copy()
    df_display.columns = ["Route", "Orders", "% Total", "Avg LT (d)", "Avg Cost ($)", "Avg Delay (d)", "Delay Rate (%)"]
    st.dataframe(
        df_display, hide_index=True, use_container_width=True,
        column_config={
            "% Total":        st.column_config.ProgressColumn("% Total",        min_value=0, max_value=100, format="%.1f%%"),
            "Delay Rate (%)": st.column_config.ProgressColumn("Delay Rate (%)", min_value=0, max_value=100, format="%.1f%%"),
        }
    )

st.markdown("")
st.markdown('<div class="section-label">Product composition by route (% of route total)</div>', unsafe_allow_html=True)

df_pivot = df_prod_dist.pivot_table(index="route", columns="product", values="total_orders", fill_value=0)
df_pivot_pct = df_pivot.div(df_pivot.sum(axis=1), axis=0) * 100
df_pivot_pct = df_pivot_pct.reset_index()

fig_stacked = go.Figure()
products = [c for c in df_pivot_pct.columns if c != "route"]
for i, prod in enumerate(products):
    vals = df_pivot_pct[prod]

    fig_stacked.add_trace(go.Bar(
        name=prod,
        x=df_pivot_pct["route"],
        y=vals,
        marker_color=palette_prod[i % len(palette_prod)],
        text=[f"{v:.1f}%" if v > 7 else "" for v in vals],
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(size=9, family=FONT_MONO, color="white"),
        hovertemplate=f"{prod}<br>%{{x}}: %{{y:.1f}}%<extra></extra>"
    ))
    
fig_stacked.update_layout(
    **base_layout(height=300),
    barmode="stack",
    xaxis=styled_xaxis(title=""),
    yaxis=styled_yaxis(title="% of route volume", ticksuffix="%"),
    legend=dict(font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1), orientation="h", y=-0.22),
    margin=dict(l=8, r=8, t=10, b=10),
)
st.plotly_chart(fig_stacked, use_container_width=True)


# ═══════════════════════════════════════════════
# SECTION 3 — Operational Risk
# ═══════════════════════════════════════════════
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
st.markdown('<div class="section-title">3 · Operational Risk</div>', unsafe_allow_html=True)

col_sev, col_scatter = st.columns([1, 2])

with col_sev:
    st.markdown('<div class="section-label">Delay Severity Distribution</div>', unsafe_allow_html=True)

    severity_order  = ["none", "minor", "moderate", "severe", "critical"]
    severity_colors = {
        "none":     "#10B981",
        "minor":    "#84CC16",
        "moderate": "#F59E0B",
        "severe":   "#EF4444",
        "critical": "#7F1D1D",
    }
    df_sev = df_severity.copy()
    df_sev["delay_severity"] = pd.Categorical(df_sev["delay_severity"], categories=severity_order, ordered=True)
    df_sev = df_sev.sort_values("delay_severity")

    risk_pct = df_sev[df_sev["delay_severity"] != "none"]["pct_total"].sum()

    fig_sev = go.Figure(go.Pie(
        labels=[s.capitalize() for s in df_sev["delay_severity"]],
        values=df_sev["pct_total"],
        hole=0.58,
        marker=dict(
            colors=[severity_colors.get(s, "#9CA3AF") for s in df_sev["delay_severity"]],
            line=dict(color="#0F1117", width=2),
        ),
        # Only show label+% for slices > 5%, nothing for smaller ones
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<br>%{customdata:,} orders<extra></extra>",
        customdata=df_sev["total_orders"],
        sort=False,
    ))
    fig_sev.update_layout(
        **base_layout(height=290),
        showlegend=True,
        legend=dict(
            orientation="v",
            x=1.02, y=0.5,
            font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1),
        ),
        margin=dict(l=10, r=90, t=10, b=10),
        annotations=[dict(
            text=f"<b>{risk_pct:.1f}%</b><br>delayed",
            x=0.5, y=0.5,
            font=dict(size=14, family=FONT_SANS, color=TEXT_COLOR1),
            showarrow=False,
        )],
    )
    st.plotly_chart(fig_sev, use_container_width=True)

    df_sev_display = df_sev[["delay_severity", "total_orders", "pct_total"]].copy()
    df_sev_display.columns = ["Severity", "Orders", "% Total"]
    st.dataframe(
        df_sev_display, hide_index=True, use_container_width=True,
        column_config={
            "% Total": st.column_config.ProgressColumn("% Total", min_value=0, max_value=100, format="%.1f%%"),
        }
    )

with col_scatter:
    st.markdown('<div class="section-label">Products — Cost vs Delay Rate vs Volume</div>', unsafe_allow_html=True)

    avg_cost  = df_product["avg_cost_usd"].mean()
    avg_delay = df_product["delay_rate_pct"].mean()

    fig_scatter = go.Figure()

    fig_scatter.add_hline(
        y=avg_delay, line_dash="dot", line_color="#D1D5DB", line_width=1,
        annotation_text="avg delay", annotation_position="top right",
        annotation_font=dict(size=9, color="#9CA3AF", family=FONT_MONO),
    )
    fig_scatter.add_vline(
        x=avg_cost, line_dash="dot", line_color="#D1D5DB", line_width=1,
        annotation_text="avg cost", annotation_position="top right",
        annotation_font=dict(size=9, color="#9CA3AF", family=FONT_MONO),
    )

    for txt, x, y, ha in [
        ("High cost - Low risk",  avg_cost * 2.5, avg_delay * 0.25, "left"),
        ("High cost - High risk", avg_cost * 2.5, avg_delay * 1.75, "left"),
        ("Low cost - Low risk",   avg_cost * 0.25, avg_delay * 0.25, "right"),
        ("Low cost - High risk",  avg_cost * 0.25, avg_delay * 1.75, "right"),
    ]:
        fig_scatter.add_annotation(
            x=x, y=y, text=txt,
            showarrow=False,
            font=dict(size=8.5, color="#D1D5DB", family=FONT_MONO),
            align=ha,
        )

    for i, row in df_product.iterrows():
        fig_scatter.add_trace(go.Scatter(
            x=[row["avg_cost_usd"]],
            y=[row["delay_rate_pct"]],
            mode="markers+text",
            marker=dict(
                size=row["total_orders"] / df_product["total_orders"].max() * 55 + 12,
                color=palette_prod[i % len(palette_prod)],
                opacity=0.85,
                line=dict(width=1.5, color="white"),
            ),
            text=[row["product_category"]],
            textposition="top center",
            textfont=dict(size=9, family=FONT_SANS, color=TEXT_COLOR1),
            name=row["product_category"],
            hovertemplate=(
                f"<b>{row['product_category']}</b><br>"
                f"Avg Cost: ${row['avg_cost_usd']:,.0f}<br>"
                f"Delay Rate: {row['delay_rate_pct']:.1f}%<br>"
                f"Volume: {row['total_orders']:,}<br>"
                f"Avg Weight: {row['avg_weight_kg']:,.0f} kg"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    fig_scatter.update_layout(
        **base_layout(height=390),
        xaxis=styled_xaxis(
            title="Avg Shipping Cost (USD)",
            tickformat=",.0s",
            tickprefix="$",
        ),
        yaxis=styled_yaxis(title="Delay Rate (%)", ticksuffix="%"),
        margin=dict(l=12, r=12, t=16, b=12),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)


# ═══════════════════════════════════════════════
# SECTION 4 — OD Lane Resilience
# ═══════════════════════════════════════════════
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
st.markdown('<div class="section-title">4 · OD Lane Resilience</div>', unsafe_allow_html=True)

# ── Parse route_share JSON ──────────────────────────────────────────────────
import json as _json

def _parse_route_share(val):
    if isinstance(val, dict):
        return val
    try:
        return _json.loads(val)
    except Exception:
        return {}

df_od["_route_share"] = df_od["route_share"].apply(_parse_route_share)

# ── KPI strip ───────────────────────────────────────────────────────────────
single   = (df_od["redundancy_profile"] == "single_route").sum()
high_con = (df_od["redundancy_profile"] == "highly_concentrated").sum()
mod_con  = (df_od["redundancy_profile"] == "moderately_concentrated").sum()
diversif = (df_od["redundancy_profile"] == "well_diversified").sum()
avg_conc = df_od["route_concentration"].mean()

k1, k2, k3, k4, k5 = st.columns(5)

kpi_od_data = [
    (k1, "Single-Route Lanes",      f"{single}",        "No alternative routing","kpi-alert"),
    (k2, "Highly Concentrated",     f"{high_con}",      "Main route >70% of orders","kpi-orange"),
    (k3, "Moderately Concentrated", f"{mod_con}",       "Main route 40–70% of orders","kpi-blue"),
    (k4, "Well Diversified",        f"{diversif}",      "Route concentration <40%","kpi-ok"),
    (k5, "Avg Route Concentration", f"{avg_conc:.2f}",  "Herfindahl-style index","kpi-neutral"),
]

for col, label, value, sub, css_class in kpi_od_data:
    with col:
        st.markdown(f"""
        <div class="kpi-card {css_class}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("")

# ── Controls ────────────────────────────────────────────────────────────────
metric_options = {
    "Total Orders":         "orders",
    "Route Concentration":     "route_concentration",
    "Delay Rate (%)":          "delay_rate_pct",
    "Avg Cost ($)":            "avg_cost_usd",
    "Avg Lead Time (d)":       "avg_lead_time_days",
}
selected_metric_label = st.selectbox("Heatmap metric", list(metric_options.keys()), index=0)
selected_metric = metric_options[selected_metric_label]

col_heat, col_right = st.columns([3, 1])

# ── Heatmap ─────────────────────────────────────────────────────────────────
with col_heat:
    st.markdown('<div class="section-label">OD Heatmap — selected metric intensity</div>', unsafe_allow_html=True)

    origins      = sorted(df_od["origin"].unique())
    destinations = sorted(df_od["destination"].unique())
    matrix = pd.DataFrame(index=origins, columns=destinations, dtype=float)
    for _, row in df_od.iterrows():
        matrix.loc[row["origin"], row["destination"]] = row[selected_metric]

    is_risk_metric = selected_metric in ("delay_rate_pct", "route_concentration")
    colorscale = "RdYlGn_r" if is_risk_metric else "Blues"

    fig_heat = go.Figure(go.Heatmap(
        z=matrix.values,
        x=destinations,
        y=origins,
        colorscale=colorscale,
        colorbar=dict(
            title=dict(text=selected_metric_label, font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1)),
            tickfont=dict(size=9, family=FONT_SANS, color=TEXT_COLOR1),
        ),
        xgap=1, ygap=1,
        hoverongaps=False,
        hovertemplate="<b>%{y} → %{x}</b><br>" + selected_metric_label + ": %{z:.3f}<extra></extra>",
        text=[[f"{v:.2f}" if not pd.isna(v) else "—" for v in row] for row in matrix.values],
        texttemplate="%{text}",
        textfont=dict(size=9, family=FONT_MONO, color=TEXT_COLOR2),
    ))
    fig_heat.update_layout(
        **base_layout(height=340),
        xaxis=dict(title="Destination", tickfont=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1), tickangle=-30, linecolor="#E5E7EB"),
        yaxis=dict(title="Origin",      tickfont=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1), linecolor="#E5E7EB"),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# ── Right column: redundancy profile + top-risk lanes ───────────────────────
with col_right:
    # Redundancy profile donut
    st.markdown('<div class="section-label">Redundancy profile</div>', unsafe_allow_html=True)
    profile_order  = ["single_route", "highly_concentrated", "moderately_concentrated", "well_diversified"]
    profile_labels = ["Single route", "Highly concentrated", "Moderately concentrated", "Well diversified"]
    profile_colors = ["#EF4444", "#F59E0B", "#3B82F6", "#10B981"]

    counts = df_od["redundancy_profile"].value_counts()
    vals   = [counts.get(p, 0) for p in profile_order]

    fig_donut = go.Figure(go.Pie(
        labels=profile_labels,
        values=vals,
        hole=0.58,
        marker=dict(colors=profile_colors, line=dict(color="#0F1117", width=2)),
        textinfo="percent",
        textposition="outside",
        textfont=dict(size=9, family=FONT_MONO, color="#FFFFFF"),
        hovertemplate="<b>%{label}</b><br>Lanes: %{value}<br>Share: %{percent}<extra></extra>",
    ))
    fig_donut.update_layout(                          
        **base_layout(height=300),
        showlegend=True,
        legend=dict(
            orientation="h",                          
            x=0.5,                                   
            y=-0.15,                                  
            xanchor="center",
            yanchor="top",
            font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1),
        ),
        margin=dict(l=10, r=10, t=10, b=80),
    )
    st.plotly_chart(fig_donut, use_container_width=True)

# ── Route share distribution scatter ────────────────────────────────────────
st.markdown('<div class="section-label">Route concentration vs delay rate — bubble = orders volume</div>', unsafe_allow_html=True)

profile_color_map = {
    "single_route":             "#EF4444",
    "highly_concentrated":      "#F59E0B",
    "moderately_concentrated":  "#3B82F6",
    "well_diversified":         "#10B981",
}

fig_scatter = go.Figure()
for profile, grp in df_od.groupby("redundancy_profile"):
    fig_scatter.add_trace(go.Scatter(
        x=grp["route_concentration"],
        y=grp["delay_rate_pct"],
        mode="markers",
        name=profile.replace("_", " ").title(),
        marker=dict(
            size=grp["orders"].apply(lambda v: max(6, min(30, v / df_od["orders"].max() * 40))),
            color=profile_color_map.get(profile, "#6B7280"),
            opacity=0.75,
            line=dict(width=0.5, color="#FFFFFF"),
        ),
        text=grp["origin"] + " → " + grp["destination"],
        customdata=grp[["orders", "route_count", "avg_cost_usd"]].values,
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Concentration: %{x:.3f}<br>"
            "Delay rate: %{y:.1f}%<br>"
            "Orders: %{customdata[0]}<br>"
            "Routes used: %{customdata[1]}<br>"
            "Avg cost: $%{customdata[2]:.0f}<extra></extra>"
        ),
    ))

fig_scatter.update_layout(
    **base_layout(height=300),
    xaxis=dict(title="Route Concentration (HHI)", tickfont=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1), gridcolor="#F3F4F6"),
    yaxis=dict(title="Delay Rate (%)",            tickfont=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1), gridcolor="#F3F4F6"),
    legend=dict(font=dict(size=9, family=FONT_SANS, color=TEXT_COLOR1), orientation="h", y=-0.15),
    margin=dict(l=10, r=10, t=10, b=40),
)
st.plotly_chart(fig_scatter, use_container_width=True)

# ── Detailed lane analysis ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Detailed Lane Analysis</div>', unsafe_allow_html=True)

origins = sorted(df_od["origin"].unique())
destinations = sorted(df_od["destination"].unique())

c1, c2 = st.columns(2)
with c1:
    selected_origin = st.selectbox("Origin", origins, index=origins.index("Shanghai") if "Shanghai" in origins else 0)
with c2:
    selected_dest = st.selectbox("Destination", destinations, index=destinations.index("Rotterdam") if "Rotterdam" in destinations else 0)

lane_data = df_od[(df_od["origin"] == selected_origin) & (df_od["destination"] == selected_dest)]

if not lane_data.empty:
    row = lane_data.iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    
    metrics = [
        (m1, "Volume", f"{row['orders']}", "Total Orders"),
        (m2, "Avg Cost", f"${row['avg_cost_usd']:,.0f}", "Per Order"),
        (m3, "Lead Time", f"{row['avg_lead_time_days']}d", "Average Door-to-Door"),
        (m4, "Delay Rate", f"{row['delay_rate_pct']}%", "Reliability Index"),
    ]
    
    # KPIs cards
    for col, label, val, sub in metrics:
        with col:
            st.markdown(f"""
            <div class="kpi-card kpi-neutral" style="min-height:100px; padding: 0.6rem 0.8rem;">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value" style="font-size: 1.2rem;">{val}</div>
                <div class="kpi-sub" style="font-size: 0.65rem;">{sub}</div>
            </div>""", unsafe_allow_html=True)

    # Donut + Context
    st.markdown('<hr style="border:0.5px solid #2A2D3A; margin: 2rem 0;">', unsafe_allow_html=True)
    col_chart, col_info = st.columns([1.6, 1])

    with col_chart:
        st.markdown('<div class="section-label">Route Share Distribution</div>', unsafe_allow_html=True)
        
        share_data = row["_route_share"]
        if share_data:
            labels = list(share_data.keys())
            values = list(share_data.values())
            colors_for_donut = [ROUTE_COLORS.get(label, DEFAULT_ROUTE_COLOR) for label in labels]
            
            fig_lane_donut = go.Figure(go.Pie(
                labels=labels,
                values=values,
                hole=0.58,
                marker=dict(colors=profile_colors, line=dict(color="#0F1117", width=2)),
                textinfo="label + percent",
                textfont=dict(size=9, family=FONT_MONO, color="#FFFFFF"),
                textposition='outside',
                showlegend=True
            ))
            
            fig_lane_donut.update_layout(
                margin=dict(t=30, b=30, l=35, r=35),
                height=290,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=0.75,
                    font=dict(family="IBM Plex Mono", size=10, color="#9CA3AF")
                )
            )
            st.plotly_chart(fig_lane_donut, use_container_width=True)

    with col_info:
        st.markdown('<div class="section-label">Resilience Profile</div>', unsafe_allow_html=True)
        profile = row['redundancy_profile'].replace('_', ' ').title()
        
        color_map = {"Single Route": "#EF4444", "Highly Concentrated": "#F59E0B", 
                    "Moderately Concentrated": "#3B82F6", "Well Diversified": "#10B981"}
        p_color = color_map.get(profile, "#6B7280")
        
        st.markdown(f"""
        <div style="background: #1A1D27; border: 1px solid #2A2D3A; border-left: 4px solid {p_color}; 
                    border-radius: 8px; padding: 1.5rem; min-height: 240px; display: flex; flex-direction: column; justify-content: center;">
            <div style="color: {p_color}; font-family: 'IBM Plex Sans'; font-weight: 700; font-size: 1.2rem; margin-bottom: 0.8rem;">
                {profile}
            </div>
            <p style="font-family: 'IBM Plex Sans'; font-size: 0.9rem; color: #E5E7EB; line-height: 1.6; margin: 0;">
                This lane operates via <strong>{row['route_count']}</strong> distinct routes. 
                The concentration (HHI) is <strong>{row['route_concentration']:.3f}</strong>.
                <br><br>
                <span style="color: #9CA3AF; font-style: italic;">
                    Risk Alert: {'High dependency detected. Any disruption on the primary route will severely impact lead times.' if row['route_concentration'] > 0.7 else 'Diversification looks stable.'}
                </span>
            </p>
        </div>
        """, unsafe_allow_html=True)

else:
    st.warning(f"No data found for the lane: {selected_origin} ➔ {selected_dest}")