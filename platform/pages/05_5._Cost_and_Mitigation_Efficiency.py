import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from shared.analysis_store import load_block_data
from shared.colors import DEFAULT_PALETTE, infer_color_map
from shared.ui_helpers import render_section_header

st.set_page_config(page_title="Cost & Mitigation Efficiency", layout="wide")

FONT_SANS   = "IBM Plex Sans, sans-serif"
FONT_MONO   = "IBM Plex Mono, monospace"
GRID_COLOR  = "#2A2D3A"
AXIS_COLOR  = "#6B7280"
TEXT_COLOR1  = "#E5E7EB"
TEXT_COLOR2  = "#1A1D27"
TRANSPARENT = "rgba(0,0,0,0)"

MITIGATION_COLORS = {
    "Expedited Air Freight": "#F59E0B",
    "Re-routing":            "#3B82F6",
    "Standard Shipping":     "#6B7280",
}
EFFECTIVENESS_COLORS = {
    "fully_effective":     "#10B981",
    "partially_effective": "#F59E0B",
    "not_effective":       "#EF4444",
}

def base_layout(**kwargs):
    defaults = dict(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font=dict(family=FONT_SANS, color=TEXT_COLOR1),
        hoverlabel=dict(
            bgcolor="#1A1D27", bordercolor="#374151",
            font=dict(family=FONT_SANS, size=12, color=TEXT_COLOR1),
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
.divider-line { border: none; border-top: 1px solid #2A2D3A; margin: 1.75rem 0; }

/* Baseline comparison card */
.baseline-group { margin-bottom: 0.5rem; }
.baseline-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem; 
    font-weight: 600;
    letter-spacing: 0.12em; 
    text-transform: uppercase;
    color: #6B7280; 
    margin-bottom: 0.8rem;
    height: 1.2rem;
    display: flex;
    align-items: center;
}
.baseline-card {
    background: #1A1D27; 
    border: 1px solid #2A2D3A;
    border-radius: 8px; 
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    border-left-width: 3px;
    height: 75px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.bc-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem; font-weight: 600;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: #6B7280; margin-bottom: 0.15rem;
}
.bc-value { font-size: 1.35rem; font-weight: 700; color: #F9FAFB; line-height: 1.1; }
.bc-delta { font-size: 0.75rem; margin-top: 0.2rem; font-family: 'IBM Plex Mono', monospace; }

/* Mitigation cards */
.mit-card {
    background: #1A1D27; border: 1px solid #2A2D3A;
    border-radius: 10px; padding: 1rem 1.1rem;
    border-left-width: 3px; height: 100%;
}
.mit-card-title {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.9rem; font-weight: 700; margin-bottom: 0.65rem;
}
.mit-metric { margin-bottom: 0.45rem; }
.mit-metric-val {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.15rem; font-weight: 700; color: #F9FAFB; line-height: 1.1;
}
.mit-metric-lbl {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.58rem; font-weight: 600;
    letter-spacing: 0.1em; text-transform: uppercase; color: #6B7280;
}
.progress-bar-bg { height: 3px; background: #2A2D3A; border-radius: 2px; margin-top: 0.15rem; }
.progress-bar-fill { height: 3px; border-radius: 2px; }

/* Callout */
.callout-box {
    background: #1C1A0F; border: 1px solid #78350F;
    border-left: 4px solid #F59E0B; border-radius: 6px;
    padding: 0.8rem 1rem; margin-bottom: 1rem;
    font-size: 0.85rem; color: #FCD34D;
}
.callout-box strong { font-family: 'IBM Plex Mono', monospace; color: #FCD34D; }

/* Low-N warning */
.lown-warn {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem; color: #6B7280;
    background: #1A1D27; border: 1px solid #2A2D3A;
    border-radius: 4px; padding: 0.2rem 0.5rem;
    display: inline-block; margin-top: 0.4rem;
}

[data-testid="stDataFrame"] * { font-family: 'IBM Plex Sans', sans-serif !important; }
[data-testid="stSelectbox"] label {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important; color: #6B7280 !important;
    text-transform: uppercase; letter-spacing: 0.08em;
}
</style>
""", unsafe_allow_html=True)


# HEADER
st.markdown('<div class="section-label">Block 5</div>', unsafe_allow_html=True)
st.markdown("# Cost Analysis & Mitigation Efficiency")
st.markdown(
    "Economic impact of disruptions and effectiveness of mitigation responses — "
    "cost increases, residual delays and context-dependent recovery rates."
)
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def load_block5_data():
    return load_block_data("block5_costs")

with st.spinner("Loading cost and mitigation data..."):
    try:
        data = load_block5_data()
    except FileNotFoundError:
        st.warning(
            "No analysis data is available for Cost Analysis & Mitigation Efficiency."
        )
        st.stop()
    except Exception:
        st.warning(
            "Cost Analysis & Mitigation Efficiency is currently unavailable. "
            "The page cannot render without the cached analysis outputs."
        )
        st.stop()

df_baseline  = data["disruption_cost_baseline"]
df_by_type   = data["cost_of_disruption_by_type"]
df_mit_sum   = data["mitigation_action_summary"]
df_mit_disr  = data["mitigation_by_disruption"]
df_mit_ctx   = data["mitigation_by_context"]
df_air       = data["expedited_air_usage"]

# PREPROCESS
disruption_types = sorted(df_by_type["disruption_type"].dropna().unique())
COLOR_MAP = infer_color_map("disruption_type", disruption_types) or {
    value: DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)]
    for i, value in enumerate(disruption_types)
}


# SECTION 1 - Baseline economic impact

render_section_header("1 · Economic impact of disruptions")

if not df_baseline.empty:
    disrupted     = df_baseline[df_baseline["is_disrupted"] == True]
    non_disrupted = df_baseline[df_baseline["is_disrupted"] == False]

    if not disrupted.empty and not non_disrupted.empty:
        d  = disrupted.iloc[0]
        nd = non_disrupted.iloc[0]

        # Metrics calculation
        m_list = [
            {
                "label": "Cost vs Baseline",
                "d_val": f"{d['avg_cost_vs_baseline_pct']:.2f}%",
                "nd_val": f"{nd['avg_cost_vs_baseline_pct']:.2f}%",
                "delta": f"+{(d['avg_cost_vs_baseline_pct'] - nd['avg_cost_vs_baseline_pct']):.2f}%",
                "color": "#EF4444"
            },
            {
                "label": "Avg Delay Days",
                "d_val": f"{d['avg_delay_days']:.2f}d",
                "nd_val": f"{nd['avg_delay_days']:.2f}d",
                "delta": f"+{(d['avg_delay_days'] - nd['avg_delay_days']):.2f}d",
                "color": "#EF4444"
            },
            {
                "label": "Delay Rate",
                "d_val": f"{d['delay_rate_pct']:.2f}%",
                "nd_val": f"{nd['delay_rate_pct']:.2f}%",
                "delta": f"+{(d['delay_rate_pct'] - nd['delay_rate_pct']):.2f}%",
                "color": "#EF4444"
            }
        ]

        col_d, col_nd, col_delta = st.columns(3)

        with col_d:
            st.markdown('<div class="baseline-header">Disrupted</div>', unsafe_allow_html=True)
            for m in m_list:
                st.markdown(f"""<div class="baseline-card" style="border-left-color:#EF4444">
                    <div class="bc-label">{m['label']}</div>
                    <div class="bc-value">{m['d_val']}</div>
                </div>""", unsafe_allow_html=True)

        with col_nd:
            st.markdown('<div class="baseline-header">Non-disrupted</div>', unsafe_allow_html=True)
            for m in m_list:
                st.markdown(f"""<div class="baseline-card" style="border-left-color:#10B981">
                    <div class="bc-label">{m['label']}</div>
                    <div class="bc-value">{m['nd_val']}</div>
                </div>""", unsafe_allow_html=True)

        with col_delta:
            st.markdown('<div class="baseline-header">Δ Disruption penalty</div>', unsafe_allow_html=True)
            for m in m_list:
                st.markdown(f"""<div class="baseline-card" style="border-left-color:{m['color']}">
                    <div class="bc-label">{m['label']} penalty</div>
                    <div class="bc-value" style="color:{m['color']};">{m['delta']}</div>
                </div>""", unsafe_allow_html=True)



# SECTION 2 - Disruption cost profile

st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
render_section_header("2 · Disruption cost profile")

if not df_by_type.empty:
    col_bar, col_radar = st.columns([5, 4])

    with col_bar:
        st.markdown('<div class="section-label">Cost vs baseline (bar) i P95 delay days (line)</div>', unsafe_allow_html=True)

        fig_cost = make_subplots(specs=[[{"secondary_y": True}]])

        for i, (_, row) in enumerate(df_by_type.iterrows()):
            fig_cost.add_trace(go.Bar(
                name=row["disruption_type"],
                x=[row["disruption_type"]],
                y=[row["avg_cost_vs_baseline_pct"]],
                marker_color=COLOR_MAP.get(row["disruption_type"], DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)]),
                opacity=0.85,
                text=[f"{row['avg_cost_vs_baseline_pct']:.1f}%"],
                textposition="outside",
                textfont=dict(size=10, family=FONT_MONO, color=TEXT_COLOR1),
                hovertemplate=(
                    f"<b>{row['disruption_type']}</b><br>"
                    f"Cost vs Baseline: {row['avg_cost_vs_baseline_pct']:.2f}%<br>"
                    f"Avg Delay days: {row['avg_delay_days']:.2f}d<br>"
                    f"Delay rate: {row['delay_rate_pct']:.2f}%<br>"
                    f"P95 Delay Days: {row['p95_delay_days']:.2f}d<br>"
                    f"Orders: {int(row['total_orders']):,}"
                    "<extra></extra>"
                ),
                showlegend=False,
            ), secondary_y=False)

        fig_cost.add_trace(go.Scatter(
            x=df_by_type["disruption_type"],
            y=df_by_type["p95_delay_days"],
            name="P95 Delay Days",
            mode="lines+markers",
            line=dict(color="#E5E7EB", width=2, dash="dot"),
            marker=dict(size=8, color="#E5E7EB", line=dict(width=1.5, color="#0F1117")),
            hovertemplate="<b>%{x}</b><br>P95 Delay: %{y:.2f}d<extra></extra>",
        ), secondary_y=True)
        
        fig_cost.add_trace(go.Scatter(
            x=df_by_type["disruption_type"],
            y=df_by_type["avg_delay_days"],
            name="Avg Delay Days",
            mode="lines+markers",
            line=dict(color="#E5E7EB", width=2, dash="dash"),
            marker=dict(size=7, color="#E5E7EB", line=dict(width=1.5, color="#0F1117")),
            hovertemplate="<b>%{x}</b><br>Avg Delay: %{y:.2f}d<extra></extra>",
        ), secondary_y=True)

        fig_cost.update_layout(
            **base_layout(height=450),
            legend=dict(orientation="h", y=1.1, x=0,
                        font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1)),
            margin=dict(l=12, r=55, t=30, b=12),
        )
        fig_cost.update_yaxes(**styled_yaxis(title="Avg Cost vs Baseline (%)"), secondary_y=False)
        fig_cost.update_yaxes(
            title_text="Delay days",
            title_font=dict(family=FONT_SANS, size=11, color=AXIS_COLOR),
            tickfont=dict(family=FONT_SANS, size=10, color=AXIS_COLOR),
            gridcolor=GRID_COLOR, zeroline=False,
            secondary_y=True,
        )
        fig_cost.update_xaxes(**styled_xaxis())
        st.plotly_chart(fig_cost, width='stretch')
        st.caption(
            "Bars represent average cost vs baseline. Dotted line shows P95 delay, "
            "while dashed line shows average delay. Both metrics share the right-hand axis (days)."
        )
with col_radar:
    st.markdown(
        '<div class="section-label">Radar — multidimensional disruption profile</div>',
        unsafe_allow_html=True
    )

    if not df_by_type.empty:
        fig_radar = go.Figure()
        df_r = df_by_type.copy()
        
        radar_dims = [
            "avg_cost_vs_baseline_pct",
            "avg_delay_days",
            "p95_delay_days",
            "total_orders"
        ]

        categories = ["Cost vs Baseline", "Avg Delay", "P95 Delay", "Volume"]

        for c in radar_dims:
            df_r[c + "_norm"] = df_r[c].rank(pct=True)

        for i, (_, row) in enumerate(df_r.iterrows()):
            color = COLOR_MAP.get(row["disruption_type"], DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)])

            vals = [
                row["avg_cost_vs_baseline_pct_norm"],
                row["avg_delay_days_norm"],
                row["p95_delay_days_norm"],
                row["total_orders_norm"]
            ]
            vals += [vals[0]]

            fig_radar.add_trace(go.Scatterpolar(
                r=vals,
                theta=categories + [categories[0]],
                fill="toself",
                fillcolor=color,
                opacity=0.3,
                line=dict(color=color, width=2),
                name=row["disruption_type"],
            ))

        fig_radar.update_layout(
            **base_layout(height=450),
            polar=dict(
                bgcolor=TRANSPARENT,
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    showticklabels=False,
                    gridcolor="rgba(229, 231, 235, 0.3)"
                ),
                angularaxis=dict(
                    tickfont=dict(size=11, family=FONT_SANS, color=TEXT_COLOR1)
                ),
            ),
            legend=dict(
                font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1),
                orientation="h",
                y=-0.18
            ),
            margin=dict(l=10, r=10, t=40, b=30),
        )

        st.plotly_chart(fig_radar, width='stretch')


# SECTION 3 - Global mitigation effectiveness

st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
render_section_header("3 · Global mitigation effectiveness")

if not df_mit_sum.empty:
    # Cards
    st.markdown('<div class="section-label">Metrics by mitigation action</div>', unsafe_allow_html=True)
    mit_cols = st.columns(len(df_mit_sum))
    max_eff  = df_mit_sum["effectiveness_rate_pct"].max()
    max_prem = df_mit_sum["avg_cost_vs_baseline_pct"].max()
    max_del  = df_mit_sum["residual_delay_days"].max()
    max_rec  = df_mit_sum["recovered_within_schedule_pct"].max()

    for i, (_, row) in enumerate(df_mit_sum.iterrows()):
        color = MITIGATION_COLORS.get(row["mitigation_action"], "#6B7280")
        w_eff  = row["effectiveness_rate_pct"] / max_eff * 100 if max_eff > 0 else 0
        w_prem = row["avg_cost_vs_baseline_pct"]    / max_prem * 100 if max_prem > 0 else 0
        w_del  = row["residual_delay_days"]      / max_del * 100  if max_del > 0 else 0
        w_rec  = row["recovered_within_schedule_pct"] / max_rec * 100 if max_rec > 0 else 0

        with mit_cols[i]:
            st.html(f"""
            <div class="mit-card" style="border-left-color:{color}">
                <div class="mit-card-title" style="color:{color}">
                    {row['mitigation_action']}
                    <span style="font-size:0.65rem;color:#6B7280;display:block;
                                 font-family:'IBM Plex Mono',monospace;margin-top:0.1rem">
                        {int(row['total_cases']):,} cases
                    </span>
                </div>

                <div class="mit-metric">
                    <div class="mit-metric-val">{row['effectiveness_rate_pct']:.1f}%</div>
                    <div class="mit-metric-lbl">Effectiveness rate</div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill"
                             style="width:{w_eff:.1f}%;background:{color};opacity:0.9"></div>
                    </div>
                </div>

                <div class="mit-metric">
                    <div class="mit-metric-val">+{row['avg_cost_vs_baseline_pct']:.1f}%</div>
                    <div class="mit-metric-lbl">Cost vs Baseline</div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill"
                             style="width:{w_prem:.1f}%;background:{color};opacity:0.65"></div>
                    </div>
                </div>

                <div class="mit-metric">
                    <div class="mit-metric-val">{row['residual_delay_days']:.2f}d</div>
                    <div class="mit-metric-lbl">Residual delay</div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill"
                             style="width:{w_del:.1f}%;background:{color};opacity:0.5"></div>
                    </div>
                </div>

                <div class="mit-metric">
                    <div class="mit-metric-val">{row['recovered_within_schedule_pct']:.1f}%</div>
                    <div class="mit-metric-lbl">Recovered on schedule</div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill"
                             style="width:{w_rec:.1f}%;background:{color};opacity:0.35"></div>
                    </div>
                </div>
            </div>
            """)

    st.markdown("")

    # Stacked bar
    st.markdown('<div class="section-label">Effectiveness distribution by action</div>', unsafe_allow_html=True)
    fig_stack = go.Figure()
    for eff_key, eff_label, eff_color in [
        ("fully_effective",     "Fully Effective",     "#10B981"),
        ("partially_effective", "Partially Effective", "#F59E0B"),
        ("not_effective",       "Not Effective",       "#EF4444"),
    ]:
        fig_stack.add_trace(go.Bar(
            name=eff_label,
            x=df_mit_sum["mitigation_action"],
            y=df_mit_sum[eff_key],
            marker_color=eff_color,
            opacity=0.88,
            text=df_mit_sum[eff_key],
            textposition="inside",
            textfont=dict(size=10, family=FONT_MONO, color="white"),
            hovertemplate=f"<b>%{{x}}</b><br>{eff_label}: %{{y:,}}<extra></extra>",
        ))
    fig_stack.update_layout(
        **base_layout(height=240),
        barmode="stack",
        xaxis=styled_xaxis(),
        yaxis=styled_yaxis(title="Cases"),
        legend=dict(orientation="h", y=1.1, x=0,
                    font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1)),
        margin=dict(l=12, r=12, t=30, b=12),
    )
    st.plotly_chart(fig_stack, width='stretch')


# SECTION 4 - Mitigation by disruption context

st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
render_section_header("4 · Mitigation by disruption type")

if not df_mit_disr.empty:
    disruption_types = sorted(df_mit_disr["disruption_type"].unique())
    sel_disruption = st.selectbox(
        "Disruption type",
        options=disruption_types,
        index=0,
    )

    df_filt = df_mit_disr[df_mit_disr["disruption_type"] == sel_disruption].copy()

    if not df_filt.empty:
        st.markdown("")
        card_cols = st.columns(len(df_filt))
        for i, (_, row) in enumerate(df_filt.sort_values("effectiveness_rate_pct", ascending=False).iterrows()):
            color = MITIGATION_COLORS.get(row["mitigation_action"], "#6B7280")
            cost_vs_baseline = float(row["avg_cost_vs_baseline_pct"])
            cost_vs_baseline_text = f"+{cost_vs_baseline:.1f}%" if cost_vs_baseline >= 0 else f"{cost_vs_baseline:.1f}%"
            with card_cols[i]:
                st.markdown(f"""
                <div class="mit-card" style="border-left-color:{color}">
                    <div class="mit-card-title" style="color:{color}">
                        {row['mitigation_action']}
                        <span style="font-size:0.62rem;color:#6B7280;display:block;
                                     font-family:'IBM Plex Mono',monospace;margin-top:0.1rem">
                            {int(row['total_cases']):,} cases
                        </span>
                    </div>
                    <div class="mit-metric">
                        <div class="mit-metric-val">{row['effectiveness_rate_pct']:.1f}%</div>
                        <div class="mit-metric-lbl">Effectiveness</div>
                    </div>
                    <div class="mit-metric">
                        <div class="mit-metric-val">{cost_vs_baseline_text}</div>
                        <div class="mit-metric-lbl">Cost vs Baseline</div>
                    </div>
                    <div class="mit-metric">
                        <div class="mit-metric-val">{row['residual_delay_days']:.2f}d</div>
                        <div class="mit-metric-lbl">Residual delay</div>
                    </div>
                    <div class="mit-metric">
                        <div class="mit-metric-val">{row['recovered_within_schedule_pct']:.1f}%</div>
                        <div class="mit-metric-lbl">On schedule</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("")
        st.markdown('<div class="section-label">Comparison sorted by effectiveness</div>', unsafe_allow_html=True)

        df_table = df_filt[[
            "mitigation_action", "effectiveness_rate_pct", "avg_cost_vs_baseline_pct",
            "residual_delay_days", "recovered_within_schedule_pct",
            "fully_effective", "partially_effective", "not_effective", "total_cases"
        ]].sort_values("effectiveness_rate_pct", ascending=False).copy()
        df_table.columns = [
            "Action", "Effectiveness (%)", "Cost vs Baseline (%)",
            "Residual Delay (d)", "On Schedule (%)",
            "Fully", "Partially", "Not  ⚠", "Total Cases"
        ]
        st.dataframe(
            df_table, hide_index=True, width='stretch',
            column_config={
                "Effectiveness (%)": st.column_config.ProgressColumn(
                    "Effectiveness (%)", min_value=0, max_value=100, format="%.1f%%"),
                "On Schedule (%)": st.column_config.ProgressColumn(
                    "On Schedule (%)", min_value=0, max_value=100, format="%.1f%%"),
            }
        )


# SECTION 5 - Full context mitigation

st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
render_section_header("5 · Full context mitigation")
st.markdown('<div class="section-label">Disruption × Route × Risk level → Heatmap by action mitigation</div>', unsafe_allow_html=True)

LOW_N_THRESHOLD = 5

if not df_mit_ctx.empty:
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        ctx_disruptions = ["All"] + sorted(df_mit_ctx["disruption_type"].unique().tolist())
        sel_ctx_disr = st.selectbox("Disruption type", ctx_disruptions, index=0)
    with f_col2:
        ctx_routes = ["All"] + sorted(df_mit_ctx["route"].unique().tolist())
        sel_ctx_route = st.selectbox("Route", ctx_routes, index=0)
    with f_col3:
        risk_order = ["low", "medium", "high", "critical"]
        ctx_risks = ["All"] + [r for r in risk_order if r in df_mit_ctx["risk_level"].str.lower().unique()]
        sel_ctx_risk = st.selectbox("Risk level", ctx_risks, index=0)

    df_ctx = df_mit_ctx.copy()
    df_ctx["risk_level"] = df_ctx["risk_level"].str.lower()
    if sel_ctx_disr  != "All": df_ctx = df_ctx[df_ctx["disruption_type"] == sel_ctx_disr]
    if sel_ctx_route != "All": df_ctx = df_ctx[df_ctx["route"]            == sel_ctx_route]
    if sel_ctx_risk  != "All":  df_ctx = df_ctx[df_ctx["risk_level"]       == sel_ctx_risk]

    if df_ctx.empty:
        st.markdown(
            '<div class="callout-box">⚠ No data available for the selected filter combination.</div>',
            unsafe_allow_html=True,
        )
    else:
        metric_map = {
            "Effectiveness (%)":  "effectiveness_rate_pct",
            "Cost vs Baseline (%)":   "avg_cost_vs_baseline_pct",
            "Residual Delay (d)": "residual_delay_days",
            "On Schedule (%)":    "recovered_within_schedule_pct",
        }
        sel_metric   = st.selectbox("Metric", list(metric_map.keys()), index=0)
        metric_field = metric_map[sel_metric]

        suffix = "d" if "Delay" in sel_metric else "%"

        df_agg_ctx = (
            df_ctx.groupby(["mitigation_action", "disruption_type"])
            .agg(
                value=(metric_field, "mean"),
                total_cases=("total_cases", "sum"),
            )
            .reset_index()
        )

        heatmap_df = df_agg_ctx.pivot(
            index="mitigation_action",
            columns="disruption_type",
            values="value",
        )
        cases_df = df_agg_ctx.pivot(
            index="mitigation_action",
            columns="disruption_type",
            values="total_cases",
        )

        # text matrix: value + low-N warning
        text_matrix = []
        for r_idx, action in enumerate(heatmap_df.index):
            row_text = []
            for c_idx, disr in enumerate(heatmap_df.columns):
                val   = heatmap_df.loc[action, disr]
                cases = cases_df.loc[action, disr]
                if pd.isna(val):
                    row_text.append("—")
                else:
                    prefix = "⚠ " if (not pd.isna(cases) and cases < LOW_N_THRESHOLD) else ""
                    row_text.append(f"{prefix}{val:.1f}{suffix}")
            text_matrix.append(row_text)

        colorscale_map = {
            "effectiveness_rate_pct":         "RdYlGn",
            "avg_cost_vs_baseline_pct":       "Reds",
            "residual_delay_days":            "Reds",
            "recovered_within_schedule_pct":  "Greens",
        }
        colorscale = colorscale_map.get(metric_field, "Viridis")

        fig_ctx = go.Figure(go.Heatmap(
            z=heatmap_df.values,
            x=heatmap_df.columns.tolist(),
            y=heatmap_df.index.tolist(),
            colorscale=colorscale,
            xgap=3,
            ygap=3,
            colorbar=dict(
                title=dict(text=sel_metric, font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR1)),
                tickfont=dict(size=9, family=FONT_SANS, color=TEXT_COLOR1),
                thickness=12,
            ),
            text=text_matrix,
            texttemplate="%{text}",
            textfont=dict(size=11, family=FONT_MONO, color="#1A1D27"),
            hoverongaps=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Disruption: %{x}<br>"
                f"{sel_metric}: %{{z:.2f}}{suffix}<br>"
                "Cases: %{customdata}<extra></extra>"
            ),
            customdata=cases_df.values,
        ))

        fig_ctx.update_layout(
            **base_layout(height=max(300, len(heatmap_df.index) * 70 + 60)),
            xaxis=dict(
                tickfont=dict(size=11, family=FONT_SANS, color=TEXT_COLOR1),
                tickangle=-30,
                linecolor="#3D4151",
            ),
            yaxis=dict(
                tickfont=dict(size=11, family=FONT_SANS, color=TEXT_COLOR1),
                linecolor="#3D4151",
            ),
            margin=dict(l=12, r=12, t=20, b=60),
        )
        st.plotly_chart(fig_ctx, width='stretch')

        # Low-N warning global
        any_low_n = (cases_df < LOW_N_THRESHOLD).any(skipna=True).any()
        if any_low_n:
            st.caption(f"⚠ Les cel·les marcades amb ⚠ tenen menys de {LOW_N_THRESHOLD} casos — valors poden no ser estadísticament representatius.")

        with st.expander("Detailed table by context"):
            st.caption("Tip: you can sort directly in the table by clicking on column headers.")
            df_ctx_display = df_ctx[[
                "disruption_type", "route", "risk_level", "mitigation_action",
                "total_cases", "effectiveness_rate_pct", "avg_cost_vs_baseline_pct",
                "residual_delay_days", "recovered_within_schedule_pct",
            ]].sort_values("disruption_type", ascending=False).copy()
            df_ctx_display.columns = [
                "Disruption", "Route", "Risk", "Action",
                "Cases", "Effectiveness (%)", "Cost vs Baseline (%)",
                "Residual Delay (d)", "On Schedule (%)",
            ]
            st.dataframe(
                df_ctx_display, hide_index=True, width='stretch',
                column_config={
                    "Effectiveness (%)": st.column_config.ProgressColumn(
                        "Effectiveness (%)", min_value=0, max_value=100, format="%.1f%%"),
                    "On Schedule (%)": st.column_config.ProgressColumn(
                        "On Schedule (%)", min_value=0, max_value=100, format="%.1f%%"),
                }
            )

# SECTION 6 - Expedited air usage

st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
render_section_header("6 · Expedited air usage")
st.markdown('<div class="section-label">% Expedited Air Freight usage by disruption</div>', unsafe_allow_html=True)

if not df_air.empty:
    avg_air_share = df_air["expedited_air_share_pct"].mean()

    df_air_sorted = df_air.sort_values("expedited_air_share_pct", ascending=True)

    fig_air = go.Figure()

    # Baseline reference
    fig_air.add_vline(
        x=avg_air_share, line_dash="dot", line_color="#4B5563", line_width=1.5,
        annotation_text=f"avg {avg_air_share:.1f}%",
        annotation_position="top",
        annotation_font=dict(size=9, color="#6B7280", family=FONT_MONO),
    )

    fig_air.add_trace(go.Bar(
        x=df_air_sorted["expedited_air_share_pct"],
        y=df_air_sorted["disruption_type"],
        orientation="h",
        marker_color=[
            COLOR_MAP.get(row["disruption_type"], "#6B7280")
            for _, row in df_air_sorted.iterrows()
        ],
        opacity=0.88,
        text=[
            f"{row['expedited_air_share_pct']:.1f}%"
            for _, row in df_air_sorted.iterrows()
        ],
        textposition="outside",
        textfont=dict(size=10, family=FONT_MONO, color=TEXT_COLOR1),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Air usage: %{x:.1f}%<br>"
            "Cases: %{customdata[0]:,}<br>"
            "Avg cost vs baseline: +%{customdata[1]:.1f}%"
            "<extra></extra>"
        ),
        customdata=df_air_sorted[["expedited_air_cases", "avg_cost_vs_baseline_pct_when_expedited"]].values,
    ))

    fig_air.update_layout(
        **base_layout(height=350),
        xaxis=styled_xaxis(title="% of orders using Expedited Air Freight", ticksuffix="%"),
        yaxis=styled_yaxis(showgrid=False),
        margin=dict(l=12, r=150, t=16, b=12),
    )
    st.plotly_chart(fig_air, width='stretch')
    st.caption(
        "The dotted line represents the global average usage of expedited air freight. "
        "Bars above the line indicate disruptions that more frequently trigger "
        "this emergency response. The label shows the associated cost premium when activated."
    )