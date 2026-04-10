import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from connection import get_neo4j_driver
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
# CSS — force light mode + IBM Plex typography
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
}
.kpi-neutral { border-left-color: #4B5563; }
.kpi-ok      { border-left-color: #10B981; }
.kpi-alert   { border-left-color: #EF4444; }

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
df_route     = data["shipments_by_route"]
df_mode      = data["shipments_by_transport_mode"]
df_product   = data["shipments_by_product"]
df_prod_dist = data["product_distribution"]
df_severity  = data["delay_severity_distribution"]
df_od        = data["od_redundancy_profile"]
df_temporal  = data["temporal_trend"].copy()
df_temporal["date"] = pd.to_datetime(
    df_temporal["year"].astype(str) + "-" + df_temporal["month"].astype(str) + "-01"
)

palette_prod = px.colors.qualitative.Safe


# ═══════════════════════════════════════════════
# SECCIÓ 1 — El sistema en xifres
# ═══════════════════════════════════════════════
st.markdown('<div class="section-title">1 · El sistema en xifres</div>', unsafe_allow_html=True)

col_v, col_r = st.columns(2)

with col_v:
    st.markdown('<div class="section-label">Volum & Operativa</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="kpi-card kpi-neutral">
            <div class="kpi-label">Total Orders</div>
            <div class="kpi-value">{int(kpis['total_orders']):,}</div>
            <div class="kpi-sub">Enviaments analitzats</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card kpi-neutral">
            <div class="kpi-label">Avg Lead Time</div>
            <div class="kpi-value">{kpis['avg_actual_lead_time_days']:.1f}<span style="font-size:1rem;font-weight:400;color:#9CA3AF"> d</span></div>
            <div class="kpi-sub">P95: {kpis['p95_actual_lead_time_days']:.1f} dies</div>
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
    st.markdown('<div class="section-label">Risc & Cost</div>', unsafe_allow_html=True)
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
    "Shipments": "total_orders",
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
# SECCIÓ 2 — Distribució del tràfic
# ═══════════════════════════════════════════════
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
st.markdown('<div class="section-title">2 · Distribució del tràfic</div>', unsafe_allow_html=True)

col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown('<div class="section-label">Volum per ruta</div>', unsafe_allow_html=True)
    df_route_sorted = df_route.sort_values("total_shipments", ascending=True)
    colors = ["#F59E0B" if "suez" in r.lower() else "#1D4ED8" for r in df_route_sorted["route"]]

    fig_route = go.Figure(go.Bar(
        x=df_route_sorted["total_shipments"],
        y=df_route_sorted["route"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:,}  ({p:.1f}%)" for v, p in zip(df_route_sorted["total_shipments"], df_route_sorted["pct_total"])],
        textposition="outside",
        textfont=dict(size=10, family=FONT_MONO, color=TEXT_COLOR1),
    ))
    fig_route.update_layout(
        **base_layout(height=285),
        xaxis=styled_xaxis(title="Shipments"),
        yaxis=styled_yaxis(showgrid=False),
        margin=dict(l=8, r=90, t=10, b=10),
    )
    st.plotly_chart(fig_route, use_container_width=True)

with col_right:
    st.markdown('<div class="section-label">Perfil per ruta — Lead Time, Cost & Delay (normalitzat)</div>', unsafe_allow_html=True)

    cols_norm = ["avg_lead_time_days", "avg_cost_usd", "delay_rate_pct"]
    df_radar = df_route.copy()
    for c in cols_norm:
        mn, mx = df_radar[c].min(), df_radar[c].max()
        df_radar[c + "_norm"] = (df_radar[c] - mn) / (mx - mn) if mx > mn else 0.5

    categories = ["Lead Time", "Cost", "Delay Rate"]
    fig_radar = go.Figure()
    palette_radar = ["#1D4ED8", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]
    for i, (_, row) in enumerate(df_radar.iterrows()):
        vals = [row["avg_lead_time_days_norm"], row["avg_cost_usd_norm"], row["delay_rate_pct_norm"]]
        vals += [vals[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=vals,
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor=palette_radar[i % len(palette_radar)],
            opacity=0.3,
            line=dict(color=palette_radar[i % len(palette_radar)], width=2),
            name=row["route"],
        ))
    fig_radar.update_layout(
        **base_layout(height=285),
        polar=dict(
            bgcolor=TRANSPARENT,
            radialaxis=dict(visible=False, range=[0, 1]),
            angularaxis=dict(tickfont=dict(size=11, family=FONT_SANS, color=TEXT_COLOR1)),
        ),
        legend=dict(font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1), orientation="h", y=-0.18),
        margin=dict(l=30, r=30, t=10, b=50),
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with st.expander("📋 Taula detallada per ruta"):
    df_display = df_route[["route", "total_shipments", "pct_total", "avg_lead_time_days", "avg_cost_usd", "avg_delay_days", "delay_rate_pct"]].copy()
    df_display.columns = ["Route", "Shipments", "% Total", "Avg LT (d)", "Avg Cost ($)", "Avg Delay (d)", "Delay Rate (%)"]
    st.dataframe(
        df_display, hide_index=True, use_container_width=True,
        column_config={
            "% Total":        st.column_config.ProgressColumn("% Total",        min_value=0, max_value=100, format="%.1f%%"),
            "Delay Rate (%)": st.column_config.ProgressColumn("Delay Rate (%)", min_value=0, max_value=100, format="%.1f%%"),
        }
    )

st.markdown("")
st.markdown('<div class="section-label">Composició de producte per ruta (% sobre total ruta)</div>', unsafe_allow_html=True)

df_pivot = df_prod_dist.pivot_table(index="route", columns="product", values="total_shipments", fill_value=0)
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
# SECCIÓ 3 — Risc operatiu
# ═══════════════════════════════════════════════
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
st.markdown('<div class="section-title">3 · On hi ha risc operatiu</div>', unsafe_allow_html=True)

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
        customdata=df_sev["total_shipments"],
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

    df_sev_display = df_sev[["delay_severity", "total_shipments", "pct_total"]].copy()
    df_sev_display.columns = ["Severity", "Orders", "% Total"]
    st.dataframe(
        df_sev_display, hide_index=True, use_container_width=True,
        column_config={
            "% Total": st.column_config.ProgressColumn("% Total", min_value=0, max_value=100, format="%.1f%%"),
        }
    )

with col_scatter:
    st.markdown('<div class="section-label">Productes — Cost vs Delay Rate vs Volum</div>', unsafe_allow_html=True)

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
                size=row["total_shipments"] / df_product["total_shipments"].max() * 55 + 12,
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
                f"Volume: {row['total_shipments']:,}<br>"
                f"Avg Weight: {row['avg_weight_kg']:,.0f} kg"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    fig_scatter.update_layout(
        **base_layout(height=390),
        xaxis=styled_xaxis(
            title="Avg Shipping Cost (USD)",
            tickformat=",.0s",   # formats as 10k, 20k, etc.
            tickprefix="$",
        ),
        yaxis=styled_yaxis(title="Delay Rate (%)", ticksuffix="%"),
        margin=dict(l=12, r=12, t=16, b=12),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)


# ═══════════════════════════════════════════════
# SECCIÓ 4 — Resiliència de les lanes OD
# ═══════════════════════════════════════════════
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
st.markdown('<div class="section-title">4 · Resiliència de les lanes OD</div>', unsafe_allow_html=True)

metric_options = {
    "Total shipments":         "shipments",
    "Route Concentration (%)": "primary_route_share_pct",
    "Delay Rate (%)":          "delay_rate_pct",
    "Avg Cost ($)":            "avg_cost_usd",
    "Avg Lead Time (d)":       "avg_lead_time_days",
}
selected_metric_label = st.selectbox(
    "Mètrica del heatmap",
    options=list(metric_options.keys()),
    index=0,
)
selected_metric = metric_options[selected_metric_label]

col_heatmap, col_top = st.columns([3, 1])

with col_heatmap:
    st.markdown('<div class="section-label">Heatmap OD — intensitat per mètrica seleccionada</div>', unsafe_allow_html=True)

    origins      = sorted(df_od["origin"].unique())
    destinations = sorted(df_od["destination"].unique())
    matrix = pd.DataFrame(index=origins, columns=destinations, dtype=float)
    for _, row in df_od.iterrows():
        matrix.loc[row["origin"], row["destination"]] = row[selected_metric]

    colorscale = "RdYlGn_r" if selected_metric in ("delay_rate_pct", "primary_route_share_pct") else "Blues"

    fig_heat = go.Figure(go.Heatmap(
        z=matrix.values,
        x=destinations,
        y=origins,
        colorscale=colorscale,
        colorbar=dict(
            title=dict(text=selected_metric_label, font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1)),
            tickfont=dict(size=9, family=FONT_SANS, color=TEXT_COLOR1),
        ),
        hoverongaps=False,
        hovertemplate="<b>%{y} → %{x}</b><br>" + selected_metric_label + ": %{z:.1f}<extra></extra>",
        text=[[f"{v:.1f}" if not pd.isna(v) else "—" for v in row] for row in matrix.values],
        texttemplate="%{text}",
        textfont=dict(size=9, family=FONT_MONO, color=TEXT_COLOR2),
    ))
    fig_heat.update_layout(
        **base_layout(height=330),
        xaxis=dict(
            title="Destination",
            tickfont=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1),
            tickangle=-30,
            linecolor="#E5E7EB",
        ),
        yaxis=dict(
            title="Origin",
            tickfont=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1),
            linecolor="#E5E7EB",
        ),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

with col_top:
    st.markdown("")
    st.markdown('<div class="section-label">Redundancy profile</div>', unsafe_allow_html=True)
    redundancy_counts = df_od["redundancy_profile"].value_counts().reset_index()
    redundancy_counts.columns = ["Profile", "Count"]
    profile_colors = {
        "single_route":                 "#EF4444",
        "multi_route_but_concentrated": "#F59E0B",
        "multi_route_diversified":      "#10B981",
    }
    fig_red = go.Figure(go.Bar(
        x=redundancy_counts["Count"],
        y=redundancy_counts["Profile"].str.replace("_", " ").str.title(),
        orientation="h",
        marker_color=[profile_colors.get(p, "#6B7280") for p in redundancy_counts["Profile"]],
        text=redundancy_counts["Count"],
        textposition="outside",
        textfont=dict(size=10, family=FONT_MONO, color=TEXT_COLOR1),
    ))
    fig_red.update_layout(
        **base_layout(height=165),
        xaxis=dict(visible=False),
        yaxis=dict(
            tickfont=dict(size=9, family=FONT_SANS, color=TEXT_COLOR1),
            showgrid=False,
        ),
        margin=dict(l=8, r=35, t=8, b=8),
    )
    st.plotly_chart(fig_red, use_container_width=True)
    
st.markdown('<div class="section-subtitle">Top 10 — anàlisi de lanes</div>', unsafe_allow_html=True)

rank_options = {
    "Total Shipments": "shipments",
    "Route Concentration (%)": "primary_route_share_pct",
    "Delay (%)": "delay_rate_pct",
    "Avg Cost ($)": "avg_cost_usd",
    "Avg Lead Time (d)": "avg_lead_time_days",
}

title_map = {
    "Total Shipments": "Highest traffic",
    "Route Concentration (%)": "Highest concentration",
    "Delay (%)": "Highest delay",
    "Avg Cost ($)": "Highest cost",
    "Avg Lead Time (d)": "Longest lead time",
}

selected_rank_label = st.selectbox(
    "Rank lanes by",
    options=list(rank_options.keys()),
    index=0,
)

selected_rank_metric = rank_options[selected_rank_label]

st.markdown(
    f"<div class='section-label'>Top 10 — {title_map[selected_rank_label]}</div>",
    unsafe_allow_html=True
)

st.caption(f"Ranking metric: {selected_rank_label}")

df_top10 = (
    df_od
    .sort_values(selected_rank_metric, ascending=False)
    .head(10)[
        [
            "origin",
            "destination",
            "shipments",
            "primary_route_share_pct",
            "delay_rate_pct",
            "avg_cost_usd",
            "avg_lead_time_days",
        ]
    ]
    .rename(columns={
        "origin": "Origin",
        "destination": "Destination",
        "shipments": "Total Shipments",
        "primary_route_share_pct": "Route Concentration (%)",
        "delay_rate_pct": "Delay (%)",
        "avg_cost_usd": "Avg Cost ($)",
        "avg_lead_time_days": "Avg Lead Time (d)",
    })
)

st.dataframe(
    df_top10,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Total Shipments": st.column_config.NumberColumn(
            "Total Shipments",
            format="%.0f"
        ),
        "Route Concentration (%)": st.column_config.ProgressColumn(
            "Route Concentration (%)",
            min_value=0,
            max_value=100,
            format="%.2f%%"
        ),
        "Delay (%)": st.column_config.ProgressColumn(
            "Delay (%)",
            min_value=0,
            max_value=100,
            format="%.2f%%"
        ),
        "Avg Cost ($)": st.column_config.NumberColumn(
            "Avg Cost ($)",
            format="$%.2f"
        ),
        "Avg Lead Time (d)": st.column_config.NumberColumn(
            "Avg Lead Time (d)",
            format="%.2f"
        ),
    }
)