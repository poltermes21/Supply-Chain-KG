import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from connection import get_neo4j_driver
from analysis.queriesv2 import Block2Queries

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="Risk Analysis", layout="wide")

# ─────────────────────────────────────────────
# SHARED STYLE
# ─────────────────────────────────────────────
FONT_SANS   = "IBM Plex Sans, sans-serif"
FONT_MONO   = "IBM Plex Mono, monospace"
GRID_COLOR  = "#2A2D3A"
AXIS_COLOR  = "#6B7280"
TEXT_COLOR  = "#E5E7EB"
TRANSPARENT = "rgba(0,0,0,0)"

# Risk level palette
RISK_COLORS = {
    "low":      "#10B981",   # green
    "medium":   "#F59E0B",   # amber
    "high":     "#EF4444",   # red
    "critical": "#7C3AED",   # purple
}
RISK_ORDER = ["low", "medium", "high", "critical"]

def base_layout(**kwargs):
    defaults = dict(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font=dict(family=FONT_SANS, color=TEXT_COLOR),
        hoverlabel=dict(
            bgcolor="#1A1D27",
            bordercolor="#374151",
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
.divider-line {
    border: none; border-top: 1px solid #2A2D3A; margin: 1.75rem 0;
}

/* Risk KPI cards */
.risk-card {
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
    border: 1px solid #2A2D3A;
    position: relative;
    overflow: hidden;
}
.risk-card-low      { background: #0D1F1A; border-left: 3px solid #10B981; }
.risk-card-medium   { background: #1C1608; border-left: 3px solid #F59E0B; }
.risk-card-high     { background: #1E0F0F; border-left: 3px solid #EF4444; }
.risk-card-critical { background: #130D1F; border-left: 3px solid #7C3AED; }

.risk-card-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 0.5rem;
}
.risk-card-title {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.05rem; font-weight: 700; color: #F9FAFB;
    text-transform: capitalize;
}
.risk-card-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem; font-weight: 600;
    color: #9CA3AF; letter-spacing: 0.08em;
    text-align: right; line-height: 1.4;
}
.risk-card-score {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; color: #6B7280;
    margin-bottom: 0.75rem;
}
.risk-card-score span {
    font-size: 0.9rem; font-weight: 600; color: #D1D5DB;
}
.risk-metrics {
    display: flex; gap: 1rem; margin-bottom: 0.6rem;
}
.risk-metric {
    flex: 1;
}
.risk-metric-val {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.1rem; font-weight: 700; color: #F9FAFB;
    line-height: 1.1;
}
.risk-metric-lbl {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.58rem; font-weight: 600;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: #6B7280; margin-top: 0.1rem;
}
.progress-bar-bg {
    height: 3px; background: #2A2D3A; border-radius: 2px; margin-top: 0.15rem;
}
.progress-bar-fill {
    height: 3px; border-radius: 2px;
}

/* Callout */
.callout-box {
    background: #1C1A0F; border: 1px solid #78350F;
    border-left: 4px solid #F59E0B; border-radius: 6px;
    padding: 0.8rem 1rem; margin-bottom: 1rem;
    font-size: 0.85rem; color: #FCD34D;
}
.callout-box strong { font-family: 'IBM Plex Mono', monospace; color: #FCD34D; }

[data-testid="stDataFrame"] * { font-family: 'IBM Plex Sans', sans-serif !important; }
[data-testid="stSelectbox"] label {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.75rem !important; color: #6B7280 !important;
    text-transform: uppercase; letter-spacing: 0.08em;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">Block 2</div>', unsafe_allow_html=True)
st.markdown("# ⚠️ Multidimensional Risk Analysis")
st.markdown(
    "Risk exposure characterization across routes, products and geographies — "
    "and validation that the risk model predicts real operational outcomes."
)
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
driver = get_neo4j_driver()

# Joint risk sliders
st.sidebar.markdown("### Joint Risk Thresholds")
geo_thresh     = st.sidebar.slider("Geopolitical Risk ≥", 0.0, 1.0, 0.6, 0.05)
weather_thresh = st.sidebar.slider("Weather Severity ≥",  0.0, 1.0, 0.6, 0.05)

@st.cache_data(ttl=600)
def load_block2_data(g, w):
    return Block2Queries.run_risk_pack(driver, geo_threshold=g, weather_threshold=w)

with st.spinner("Calculating risk correlations..."):
    data = load_block2_data(geo_thresh, weather_thresh)

df_global   = data["risk_level_global"]
df_route    = data["risk_exposure_by_route"]
df_product  = data["risk_exposure_by_product"]
df_outbound = data["outbound_city_risk_exposure"]
df_inbound  = data["inbound_city_risk_exposure"]
df_joint    = data["joint_risk_exposure"]
df_lanes    = data["critical_lanes_by_risk"]

# Normalise risk_level to lowercase for consistent lookup
for df in [df_global, df_route, df_product]:
    if "risk_level" in df.columns:
        df["risk_level"] = df["risk_level"].str.lower()


# ═══════════════════════════════════════════════
# SECTION 1 — Global risk profile
# ═══════════════════════════════════════════════
st.markdown('<div class="section-title">1 · Global risk profile</div>', unsafe_allow_html=True)

# — Max values for proportional progress bars —
max_disruption = df_global["disruption_rate_pct"].max()
max_delay      = df_global["delay_rate_pct"].max()
max_delay_days = df_global["avg_delay_days"].max()

risk_cols = st.columns(4)
for i, level in enumerate(RISK_ORDER):
    row = df_global[df_global["risk_level"] == level]
    if row.empty:
        continue
    row = row.iloc[0]
    color = RISK_COLORS[level]

    pct_total    = row["pct_total"]
    n_orders     = int(row["total_orders"])
    risk_score   = row["avg_combined_risk_score"]
    disruption   = row["disruption_rate_pct"]
    delay_rate   = row["delay_rate_pct"]
    delay_days   = row["avg_delay_days"]

    # Progress bar widths (proportional to max across all levels)
    w_dis = disruption / max_disruption * 100
    w_del = delay_rate / max_delay * 100
    w_dd  = delay_days / max_delay_days * 100

    with risk_cols[i]:
        st.markdown(f"""
        <div class="risk-card risk-card-{level}">
            <div class="risk-card-header">
                <div class="risk-card-title">{level.capitalize()}</div>
                <div class="risk-card-badge">{pct_total:.1f}%<br>{n_orders:,} orders</div>
            </div>
            <div class="risk-card-score">Risk score: <span>{risk_score:.4f}</span></div>
            <div class="risk-metrics">
                <div class="risk-metric">
                    <div class="risk-metric-val">{disruption:.2f}%</div>
                    <div class="risk-metric-lbl">Disruption</div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width:{w_dis:.1f}%;background:{color};opacity:0.85"></div>
                    </div>
                </div>
                <div class="risk-metric">
                    <div class="risk-metric-val">{delay_rate:.2f}%</div>
                    <div class="risk-metric-lbl">Delay rate</div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width:{w_del:.1f}%;background:{color};opacity:0.65"></div>
                    </div>
                </div>
                <div class="risk-metric">
                    <div class="risk-metric-val">{delay_days:.2f}d</div>
                    <div class="risk-metric-lbl">Avg delay days</div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width:{w_dd:.1f}%;background:{color};opacity:0.45"></div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("")

# — Risk correlation → outcome (dot + line) —
st.markdown('<div class="section-label">Model validation — does risk predict disruption?</div>', unsafe_allow_html=True)

df_corr = df_global.copy()
df_corr["risk_level"] = pd.Categorical(df_corr["risk_level"], categories=RISK_ORDER, ordered=True)
df_corr = df_corr.sort_values("risk_level")

fig_corr = make_subplots(specs=[[{"secondary_y": True}]])

fig_corr.add_trace(go.Bar(
    x=df_corr["risk_level"].str.capitalize(),
    y=df_corr["avg_combined_risk_score"],
    name="Avg Combined Risk Score",
    marker_color=[RISK_COLORS.get(r, "#6B7280") for r in df_corr["risk_level"]],
    opacity=0.7,
    hovertemplate="<b>%{x}</b><br>Risk Score: %{y:.4f}<extra></extra>",
), secondary_y=False)


fig_corr.add_trace(go.Scatter(
    x=df_corr["risk_level"].str.capitalize(),
    y=df_corr["disruption_rate_pct"],
    mode="lines+markers",
    name="Disruption Rate (%)",
    line=dict(color="#EF4444", width=2.5, dash="dot"),
    marker=dict(size=9, line=dict(width=1, color="#0F1117")),
    hovertemplate="<b>%{x}</b><br>Disruption: %{y:.2f}%<extra></extra>",
), secondary_y=True)

fig_corr.add_trace(go.Scatter(
    x=df_corr["risk_level"].str.capitalize(),
    y=df_corr["delay_rate_pct"],
    mode="lines+markers",
    name="Delay Rate (%)",
    line=dict(color="#F59E0B", width=2.5, dash="dot"),
    marker=dict(size=9, line=dict(width=1, color="#0F1117")),
    hovertemplate="<b>%{x}</b><br>Delay: %{y:.2f}%<extra></extra>",
), secondary_y=True)

fig_corr.update_layout(
    **base_layout(height=280),
    barmode="overlay",
    legend=dict(
        orientation="h", y=1.12, x=0,
        font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR),
    ),
    margin=dict(l=12, r=50, t=30, b=12),
)
fig_corr.update_yaxes(
    **styled_yaxis(title="Rate (%)"),
    secondary_y=False,
)
fig_corr.update_yaxes(
    title_text="Avg Combined Risk Score",
    title_font=dict(family=FONT_SANS, size=11, color=AXIS_COLOR),
    tickfont=dict(family=FONT_SANS, size=10, color=AXIS_COLOR),
    gridcolor=GRID_COLOR,
    zeroline=False,
    secondary_y=True,
)
fig_corr.update_xaxes(**styled_xaxis())
st.plotly_chart(fig_corr, use_container_width=True)
st.caption("Bars (right axis) show the average risk score per level. Lines (left axis) validate that disruption and delay increase monotonically with assigned risk.")


# ═══════════════════════════════════════════════
# SECTION 2 — Risk Concentration
# ═══════════════════════════════════════════════
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
st.markdown('<div class="section-title">2 · Risk Concentration</div>', unsafe_allow_html=True)

tab_route, tab_product = st.tabs(["By Route", "By Product"])

def stacked_risk_bar(df, dimension_col, title_caption):
    """Stacked bar geo+weather + combined risk line (secondary axis)."""
    df = df.sort_values("avg_combined_risk_score", ascending=False)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        name="Geopolitical",
        x=df[dimension_col],
        y=df["avg_geopolitical_risk"],
        marker_color="#EF4444",
        opacity=0.9,
        hovertemplate="<b>%{x}</b><br>Geo Risk: %{y:.4f}<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        name="Weather",
        x=df[dimension_col],
        y=df["avg_weather_severity"],
        marker_color="#3B82F6",
        opacity=0.9,
        hovertemplate="<b>%{x}</b><br>Weather: %{y:.4f}<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        name="Avg Combined Risk Score (right axis)",
        x=df[dimension_col],
        y=df["avg_combined_risk_score"],
        mode="lines+markers",
        line=dict(color="#E5E7EB", width=1.8, dash="dot"),
        marker=dict(size=9, color="#E5E7EB", line=dict(width=1, color="#0F1117")),
        hovertemplate="<b>%{x}</b><br>Risk Combined: %{y:.4f}<extra></extra>",
    ), secondary_y=True)

    fig.update_layout(
        **base_layout(height=310),
        barmode="stack",
        legend=dict(
            orientation="h", y=1.14, x=0,
            font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR),
        ),
        margin=dict(l=12, r=55, t=35, b=12),
    )
    fig.update_xaxes(**styled_xaxis())
    fig.update_yaxes(**styled_yaxis(title="Risk index (geo + weather)"), secondary_y=False)
    fig.update_yaxes(
        title_text="Avg Combined Risk Score",
        title_font=dict(family=FONT_SANS, size=11, color=AXIS_COLOR),
        tickfont=dict(family=FONT_SANS, size=10, color=AXIS_COLOR),
        gridcolor=GRID_COLOR, zeroline=False,
        secondary_y=True,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(title_caption)


with tab_route:
    stacked_risk_bar(
        df_route, "route",
        "Routes sorted by Avg Combined Risk Score DESC. "
        "Bar composition shows dominant risk driver — geopolitical (red) vs weather (blue)."
    )

with tab_product:
    stacked_risk_bar(
        df_product, "product_category",
        "Products sorted by Avg Combined Risk Score DESC. "
        "Bar composition shows which risk type dominates each product category."
    )


# ═══════════════════════════════════════════════
# SECTION 3 — Risk by Geographic Node
# ═══════════════════════════════════════════════
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
st.markdown('<div class="section-title">3 · Risk by geographic node</div>', unsafe_allow_html=True)
st.markdown('<div class="section-label">Mirror chart — outbound (left) vs inbound (right) by combined risk score</div>', unsafe_allow_html=True)

all_cities = sorted(
    set(df_outbound["city"].tolist()) | set(df_inbound["city"].tolist())
)
# Merge both sides on city
df_mirror = pd.DataFrame({"city": all_cities})
df_mirror = df_mirror.merge(
    df_outbound[["city", "avg_combined_risk_score", "avg_geopolitical_risk", "avg_weather_severity",
                 "disruption_rate_pct", "delay_rate_pct"]].rename(columns={
        "avg_combined_risk_score": "out_combined",
        "avg_geopolitical_risk":   "out_geo",
        "avg_weather_severity":    "out_weather",
        "disruption_rate_pct":     "out_disruption",
        "delay_rate_pct":          "out_delay",
    }), on="city", how="left"
).merge(
    df_inbound[["city", "avg_combined_risk_score", "avg_geopolitical_risk", "avg_weather_severity",
                "disruption_rate_pct", "delay_rate_pct"]].rename(columns={
        "avg_combined_risk_score": "in_combined",
        "avg_geopolitical_risk":   "in_geo",
        "avg_weather_severity":    "in_weather",
        "disruption_rate_pct":     "in_disruption",
        "delay_rate_pct":          "in_delay",
    }), on="city", how="left"
).fillna(0)

# Sort by max combined risk of either side
df_mirror["max_combined"] = df_mirror[["out_combined", "in_combined"]].max(axis=1)
df_mirror = df_mirror.sort_values("max_combined", ascending=True)

fig_mirror = make_subplots(
    rows=1, cols=2,
    shared_yaxes=True,
    horizontal_spacing=0.02,
    column_titles=["← Outbound (origen)", "Inbound (destí) →"],
)

# LEFT side — outbound (values go negative for mirror effect)
fig_mirror.add_trace(go.Bar(
    name="Geoplitical",
    x=-df_mirror["out_geo"],
    y=df_mirror["city"],
    orientation="h",
    marker_color="#EF4444",
    opacity=0.9,
    hovertemplate="<b>%{y}</b> (outbound)<br>Geo: %{customdata[0]:.4f}<br>Weather: %{customdata[1]:.4f}<br>Combined: %{customdata[2]:.4f}<br>Disruption: %{customdata[3]:.1f}%<extra></extra>",
    customdata=df_mirror[["out_geo", "out_weather", "out_combined", "out_disruption"]].values,
    legendgroup="geo",
), row=1, col=1)

fig_mirror.add_trace(go.Bar(
    name="Weather",
    x=-df_mirror["out_weather"],
    y=df_mirror["city"],
    orientation="h",
    marker_color="#3B82F6",
    opacity=0.9,
    hovertemplate="<b>%{y}</b> (outbound)<br>Weather: %{customdata:.4f}<extra></extra>",
    customdata=df_mirror["out_weather"].values,
    legendgroup="weather",
), row=1, col=1)

# RIGHT side — inbound
fig_mirror.add_trace(go.Bar(
    name="Geo (inbound)",
    x=df_mirror["in_geo"],
    y=df_mirror["city"],
    orientation="h",
    marker_color="#EF4444",
    opacity=0.9,
    hovertemplate="<b>%{y}</b> (inbound)<br>Geo: %{customdata[0]:.4f}<br>Weather: %{customdata[1]:.4f}<br>Combined: %{customdata[2]:.4f}<br>Disruption: %{customdata[3]:.1f}%<extra></extra>",
    customdata=df_mirror[["in_geo", "in_weather", "in_combined", "in_disruption"]].values,
    legendgroup="geo",
    showlegend=False,
), row=1, col=2)

fig_mirror.add_trace(go.Bar(
    name="Weather (inbound)",
    x=df_mirror["in_weather"],
    y=df_mirror["city"],
    orientation="h",
    marker_color="#3B82F6",
    opacity=0.9,
    hovertemplate="<b>%{y}</b> (inbound)<br>Weather: %{customdata:.4f}<extra></extra>",
    customdata=df_mirror["in_weather"].values,
    legendgroup="weather",
    showlegend=False,
), row=1, col=2)

# Compute symmetric x range for left panel
max_out = (df_mirror["out_geo"] + df_mirror["out_weather"]).max()
max_in  = (df_mirror["in_geo"]  + df_mirror["in_weather"]).max()

fig_mirror.update_layout(
    **base_layout(height=max(320, len(df_mirror) * 38)),
    barmode="stack",
    legend=dict(
        orientation="h", y=1.08, x=0.5, xanchor="center",
        font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR),
    ),
    margin=dict(l=12, r=12, t=45, b=12),
)

# Left axis: negative values, show absolute tick labels
fig_mirror.update_xaxes(
    range=[-(max_out * 1.15), 0],
    tickvals=[-round(max_out * i / 4, 2) for i in range(5)],
    ticktext=[str(round(max_out * i / 4, 2)) for i in range(5)],
    **{k: v for k, v in styled_xaxis(title="Risk index").items() if k != "zeroline"},
    zeroline=True, zerolinecolor="#3D4151", zerolinewidth=1,
    row=1, col=1,
)
# Right axis
fig_mirror.update_xaxes(
    range=[0, max_in * 1.15],
    **{k: v for k, v in styled_xaxis(title="Risk index").items() if k != "zeroline"},
    zeroline=True, zerolinecolor="#3D4151", zerolinewidth=1,
    row=1, col=2,
)
fig_mirror.update_yaxes(
    **styled_yaxis(showgrid=False)
)

# Style column titles
fig_mirror.update_annotations(
    font=dict(family=FONT_SANS, size=11, color=AXIS_COLOR)
)

st.plotly_chart(fig_mirror, use_container_width=True)
st.caption(
    "Cities present on both sides (e.g., Shanghai) show their risk profile as origin (left) and destination (right). "
    "Solid bars = outbound, translucent = inbound. Red = geopolitical risk, blue = weather risk."
)


# ═══════════════════════════════════════════════
# SECTION 4 — Joint Risk Exposure
# ═══════════════════════════════════════════════
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
st.markdown('<div class="section-title">4 · Joint Exposure — risk overlap</div>', unsafe_allow_html=True)

# Inline threshold display
th_col1, th_col2, th_col3 = st.columns([1, 1, 3])
with th_col1:
    st.markdown(f"""
    <div style="background:#1A1D27;border:1px solid #2A2D3A;border-left:3px solid #EF4444;
                border-radius:6px;padding:0.6rem 0.9rem;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;
                    text-transform:uppercase;letter-spacing:0.1em;color:#6B7280">
            Geopolitical ≥
        </div>
        <div style="font-size:1.4rem;font-weight:700;color:#EF4444;font-family:'IBM Plex Sans',sans-serif">
            {geo_thresh:.2f}
        </div>
    </div>""", unsafe_allow_html=True)
with th_col2:
    st.markdown(f"""
    <div style="background:#1A1D27;border:1px solid #2A2D3A;border-left:3px solid #3B82F6;
                border-radius:6px;padding:0.6rem 0.9rem;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;
                    text-transform:uppercase;letter-spacing:0.1em;color:#6B7280">
            Weather ≥
        </div>
        <div style="font-size:1.4rem;font-weight:700;color:#3B82F6;font-family:'IBM Plex Sans',sans-serif">
            {weather_thresh:.2f}
        </div>
    </div>""", unsafe_allow_html=True)

st.markdown("")

if df_joint.empty:
    st.markdown("""
    <div class="callout-box">
        No orders meet both configured risk thresholds simultaneously.
    </div>""", unsafe_allow_html=True)
else:
    total_affected = int(df_joint["total_orders"].sum())
    avg_delay_joint = df_joint["avg_delay_days"].mean()
    n_routes = len(df_joint)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div style="background:#1E0F0F;border:1px solid #2A2D3A;border-left:3px solid #EF4444;
                    border-radius:8px;padding:0.8rem 1rem;">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;
                        text-transform:uppercase;letter-spacing:0.1em;color:#6B7280">
                Affected orders
            </div>
            <div style="font-size:1.5rem;font-weight:700;color:#EF4444;
                        font-family:'IBM Plex Sans',sans-serif">{total_affected:,}</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div style="background:#1A1D27;border:1px solid #2A2D3A;border-left:3px solid #F59E0B;
                    border-radius:8px;padding:0.8rem 1rem;">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;
                        text-transform:uppercase;letter-spacing:0.1em;color:#6B7280">
                Exposed Routes
            </div>
            <div style="font-size:1.5rem;font-weight:700;color:#F59E0B;
                        font-family:'IBM Plex Sans',sans-serif">{n_routes}</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div style="background:#1A1D27;border:1px solid #2A2D3A;border-left:3px solid #6B7280;
                    border-radius:8px;padding:0.8rem 1rem;">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;
                        text-transform:uppercase;letter-spacing:0.1em;color:#6B7280">
                Avg delay days
            </div>
            <div style="font-size:1.5rem;font-weight:700;color:#E5E7EB;
                        font-family:'IBM Plex Sans',sans-serif">{avg_delay_joint:.2f}d</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # Bar chart: routes by volume, color = avg_combined_risk_score
    df_joint_sorted = df_joint.sort_values("total_orders", ascending=True)

    fig_joint = go.Figure(go.Bar(
        x=df_joint_sorted["total_orders"],
        y=df_joint_sorted["route"],
        orientation="h",
        marker=dict(
            color=df_joint_sorted["avg_combined_risk_score"],
            colorscale="RdYlGn_r",
            colorbar=dict(
                title=dict(text="Combined Risk Score", font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR)),
                tickfont=dict(size=9, family=FONT_SANS, color=TEXT_COLOR),
                thickness=12,
                x=1.02,
                xpad=10
            ),
            showscale=True,
        ),
        text=[
            f"{int(v):,} orders · {r:.1f}% disrupt · {d:.1f}d delay"
            for v, r, d in zip(
                df_joint_sorted["total_orders"],
                df_joint_sorted["disruption_rate_pct"],
                df_joint_sorted["avg_delay_days"],
            )
        ],
        textposition="none",
        textfont=dict(size=9, family=FONT_MONO, color=TEXT_COLOR),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Orders: %{x:,}<br>"
            "Disruption: %{customdata[0]:.1f}%<br>"
            "Delay Rate: %{customdata[1]:.1f}%<br>"
            "Avg Delay: %{customdata[2]:.2f}d<extra></extra>"
            
        ),
        customdata=df_joint_sorted[["disruption_rate_pct", "delay_rate_pct", "avg_delay_days"]].values,
    ))
    fig_joint.update_layout(
        **base_layout(height=max(220, len(df_joint) * 55)),
        xaxis=styled_xaxis(title="Total Orders"),
        yaxis=styled_yaxis(showgrid=False),
        margin=dict(l=12, r=120, t=12, b=12),
    )
    st.plotly_chart(fig_joint, use_container_width=True)
    st.caption("Routes with simultaneous exposure to geopolitical and weather risk above the threshold. Color = combined risk score (red = higher).")


# ═══════════════════════════════════════════════
# SECTION 5 — Critical Lanes
# ═══════════════════════════════════════════════
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
st.markdown('<div class="section-title">5 · Critical lanes by risk and volume</div>', unsafe_allow_html=True)

# — Controls —
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 2, 2])

metric_labels = {
    "orders": "Volume",
    "disrupted_rate_pct": "Disruption rate",
    "delay_rate_pct": "Delay rate",
    "avg_combined_risk_score": "Risk score"
}

with ctrl_col2:
    metric = st.selectbox(
        "Highlight Top by metric",
        options=list(metric_labels.keys()),
        format_func=lambda x: metric_labels[x],
        index=0
    )

with ctrl_col3:
    view_mode = st.radio(
        "Mode",
        ["Context + Highlight", "Only Top"],
        horizontal=True
    )

lane_options = [
    f"{row['origin']} → {row['destination']}"
    for _, row in df_lanes.sort_values("orders", ascending=False).iterrows()
]

selected_lanes = st.multiselect(
    "Filter specific lanes (optional)",
    options=lane_options,
    default=[]
)

# Filtering
df_plot = df_lanes.copy()

if selected_lanes:
    selected_pairs = [
        (s.split(" → ")[0].strip(), s.split(" → ")[1].strip())
        for s in selected_lanes
    ]
    df_plot = df_plot[
        df_plot.apply(
            lambda r: (r["origin"], r["destination"]) in selected_pairs,
            axis=1
        )
    ]

# Dynamic slider 
n_lanes = len(df_plot)

if n_lanes > 1:
    with ctrl_col1:
        top_n = st.slider(
            "Top N to highlight",
            1,
            n_lanes,
            min(5, n_lanes)
        )
else:
    top_n = 1
    with ctrl_col1:
        st.markdown("""
        <div style="
            margin-top: 25px;
            width: 100%;
            background:#1A1D27;
            border:1px solid #2A2D3A;
            border-left:3px solid #6B7280;
            border-radius:6px;
            padding:0.6rem 0.9rem;
            font-size:0.8rem;
            color:#9CA3AF;
        ">
            Only 1 lane available
        </div>
        """, unsafe_allow_html=True)

# — TOP selection —
df_top = df_plot.sort_values(metric, ascending=False).head(top_n)
top_ids = set(df_top.index)

# — Mode switch —
df_plot = df_top.copy() if view_mode == "Only Top" else df_plot.copy()

# — Labels —
labels = [
    f"{row['origin']}→{row['destination']}" if idx in top_ids else ""
    for idx, row in df_plot.iterrows()
]

# — Quadrant reference lines —
avg_risk_lanes = df_lanes["avg_combined_risk_score"].mean()
avg_disr_lanes = df_lanes["disrupted_rate_pct"].mean()

padding_factor = 0.15
x_min = df_lanes["disrupted_rate_pct"].min()
x_max = df_lanes["disrupted_rate_pct"].max()
y_min = df_lanes["avg_combined_risk_score"].min()
y_max = df_lanes["avg_combined_risk_score"].max()
x_range = [
    x_min - (x_max - x_min) * padding_factor,
    x_max + (x_max - x_min) * padding_factor,
]

y_range = [
    y_min - (y_max - y_min) * padding_factor,
    y_max + (y_max - y_min) * padding_factor,
]

delay_min = df_lanes["delay_rate_pct"].min()
delay_max = df_lanes["delay_rate_pct"].max()

fig_lanes = go.Figure()

fig_lanes.add_hline(
    y=avg_risk_lanes, line_dash="dot", line_color="#4B5563", line_width=1
)
fig_lanes.add_vline(
    x=avg_disr_lanes, line_dash="dot", line_color="#4B5563", line_width=1
)

# — Bubble styling —
sizes = df_plot["orders"] / df_lanes["orders"].max() * 40 + 6

border_colors = [
    "#F59E0B" if idx in top_ids else "#0F1117"
    for idx in df_plot.index
]

border_widths = [
    3 if idx in top_ids else 1
    for idx in df_plot.index
]

opacities = [
    1.0 if idx in top_ids else 0.25
    for idx in df_plot.index
]

# — Ajuste visual en Only Top —
if view_mode == "Only Top":
    opacities = [1.0] * len(df_plot)
    border_widths = [2] * len(df_plot)

# — Customdata —
customdata = list(zip(
    df_plot["orders"],
    df_plot["delay_rate_pct"],
    df_plot["avg_combined_risk_score"],
    df_plot["origin"] + "→" + df_plot["destination"]
))

# — Scatter plot —
fig_lanes.add_trace(go.Scatter(
    x=df_plot["disrupted_rate_pct"],
    y=df_plot["avg_combined_risk_score"],
    mode="markers+text",
    text=labels,
    textposition="top center",
    marker=dict(
        size=sizes,
        color=df_plot["delay_rate_pct"],
        colorscale="RdYlGn_r",
        cmin=delay_min,
        cmax=delay_max,
        showscale=True,
        opacity=opacities,
        line=dict(width=border_widths, color=border_colors),
        colorbar=dict(title="Delay Rate (%)")
    ),
    customdata=customdata,
    hovertemplate=(
        "<b>%{customdata[3]}</b><br>"
        "Orders: %{customdata[0]:,}<br>"
        "Disruption: %{x:.1f}%<br>"
        "Delay: %{customdata[1]:.1f}%<br>"
        "Risk: %{y:.4f}<extra></extra>"
    ),
    showlegend=False,
))

fig_lanes.update_layout(
    **base_layout(height=460),
    xaxis=styled_xaxis(
        title="Disruption Rate (%)",
        ticksuffix="%",
        range=x_range
    ),
    yaxis=styled_yaxis(
        title="Avg Combined Risk Score",
        range=y_range
    ),
    margin=dict(l=12, r=80, t=16, b=12),
)

st.plotly_chart(fig_lanes, use_container_width=True)

st.caption(
    f"Top {top_n} highlighted lanes by {metric_labels[metric]}. "
    "Labels visible only for highlighted lanes. "
    "‘Only Top’ mode removes context for direct focus."
)