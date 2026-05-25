import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from shared.analysis_store import load_block_data
from shared.ui_helpers import render_section_header

st.set_page_config(page_title="Geographic Analysis", layout="wide")

FONT_SANS   = "IBM Plex Sans, sans-serif"
FONT_MONO   = "IBM Plex Mono, monospace"
GRID_COLOR  = "#2A2D3A"
AXIS_COLOR  = "#6B7280"
TEXT_COLOR  = "#E5E7EB"
TRANSPARENT = "rgba(0,0,0,0)"

COMMUNITY_PALETTE = [
    "#F59E0B", "#3B82F6", "#10B981", "#EF4444",
    "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16",
]

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
        zeroline=True,
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


def _build_pyvis_html(df_comm, df_city, df_inter, df_intra_od_pairs,
                      bridge_lanes, comm_color_map):
    """Build an interactive PyVis (vis.js) network and return the HTML string."""
    from pyvis.network import Network

    net = Network(
        height="600px", width="100%",
        bgcolor="#0F1117", font_color="#F9FAFB",
        directed=True, notebook=False, cdn_resources="remote",
    )

    net.set_options("""
    {
      "nodes": {
        "borderWidth": 2,
        "borderWidthSelected": 3,
        "font": {"size": 14, "face": "IBM Plex Sans", "color": "#F9FAFB"}
      },
      "edges": {
        "smooth": {"enabled": true, "type": "dynamic", "roundness": 0.3},
        "selectionWidth": 1.5
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -3500,
          "centralGravity": 0.25,
          "springLength": 160,
          "springConstant": 0.05,
          "damping": 0.18,
          "avoidOverlap": 0.4
        },
        "minVelocity": 0.6,
        "solver": "barnesHut",
        "stabilization": {"enabled": true, "iterations": 200, "fit": true}
      },
      "interaction": {
        "hover": true,
        "dragNodes": true,
        "zoomView": true,
        "tooltipDelay": 80,
        "navigationButtons": true
      }
    }
    """)

    city_to_comm = dict(zip(df_comm["city"], df_comm["community_id"]))
    city_in  = dict(zip(df_city["city"], df_city["inbound"]))  if not df_city.empty else {}
    city_out = dict(zip(df_city["city"], df_city["outbound"])) if not df_city.empty else {}
    max_total = max(
        (city_in.get(c, 0) + city_out.get(c, 0) for c in city_to_comm),
        default=1,
    ) or 1

    for city, cid in city_to_comm.items():
        total = city_in.get(city, 0) + city_out.get(city, 0)
        size = 14 + 26 * (total / max_total)
        color = comm_color_map.get(cid, "#6B7280")
        net.add_node(
            city, label=city,
            color={"background": color, "border": "#0F1117",
                   "highlight": {"background": color, "border": "#F9FAFB"}},
            size=size,
            title=(f"<b>{city}</b><br>Community {cid}<br>"
                   f"Inbound: {city_in.get(city, 0):,}<br>"
                   f"Outbound: {city_out.get(city, 0):,}<br>"
                   f"Total: {total:,}"),
        )

    # Intra edges: faint grey, no arrowheads
    if not df_intra_od_pairs.empty:
        intra_agg = {}
        for _, r in df_intra_od_pairs.iterrows():
            key = frozenset([r["origin"], r["destination"]])
            intra_agg[key] = intra_agg.get(key, 0) + int(r["orders"])
        for pair, orders in intra_agg.items():
            a, b = tuple(pair)
            if a not in city_to_comm or b not in city_to_comm:
                continue
            net.add_edge(
                a, b,
                color={"color": "rgba(140,140,160,0.22)",
                       "hover": "rgba(180,180,200,0.6)"},
                width=1,
                arrows={"to": {"enabled": False}, "from": {"enabled": False}},
                title=(f"<b>{a} &harr; {b}</b><br>"
                       f"Intra-community flow<br>{orders:,} orders"),
                physics=True,
            )

    # Inter edges: directional, colored by source community (one per direction)
    df_pairs = (df_inter.groupby(["from_city", "to_city"])
                .agg(orders=("orders", "sum"),
                     from_community=("from_community", "first"))
                .reset_index())
    max_inter = int(df_pairs["orders"].max()) if not df_pairs.empty else 1
    crit = {frozenset([bl["from_city"], bl["to_city"]]) for bl in bridge_lanes}

    for _, r in df_pairs.iterrows():
        u, v = r["from_city"], r["to_city"]
        if u not in city_to_comm or v not in city_to_comm:
            continue
        orders = int(r["orders"])
        if frozenset([u, v]) in crit:
            color = "#EF4444"
            width = 4.5
            tag = "<b style='color:#EF4444'>CRITICAL BRIDGE</b>"
        else:
            color = comm_color_map.get(r["from_community"], "#6B7280")
            width = 2 + 4 * (orders / max_inter)
            tag = "Inter-community bridge"
        net.add_edge(
            u, v,
            color={"color": color, "hover": color, "highlight": color},
            width=width,
            arrows={"to": {"enabled": True, "scaleFactor": 0.8}},
            title=f"<b>{u} &rarr; {v}</b><br>Orders: {orders:,}<br>{tag}",
            physics=True,
        )

    html = net.generate_html(notebook=False)

    # vis.js only renders HTML in tooltips when `title` is a DOM Element (not a
    # string). Inject a post-init step that converts every HTML title string
    # to a DOM element before the network is created, plus CSS to theme the
    # popup so it matches the dark app palette.
    tooltip_css = """
    <style>
      /* Strip PyVis's default Bootstrap card chrome so the canvas area is
         flush with the dark page background — prevents the colored edge
         lines from leaking against a white border. */
      html, body { background-color: #0F1117 !important; margin: 0; padding: 0; }
      .card {
        background-color: #0F1117 !important;
        border: none !important;
        box-shadow: none !important;
        margin: 0 !important;
        padding: 0 !important;
      }
      .card-body {
        background-color: #0F1117 !important;
        padding: 0 !important;
        overflow: hidden !important;
      }
      #mynetwork {
        background-color: #0F1117 !important;
        overflow: hidden !important;
        border: none !important;
      }
      /* Tooltip styling */
      div.vis-tooltip {
        background-color: #1A1D27 !important;
        border: 1px solid #2A2D3A !important;
        color: #F9FAFB !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 12px !important;
        line-height: 1.55 !important;
        padding: 8px 12px !important;
        border-radius: 6px !important;
        max-width: 280px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
      }
      div.vis-tooltip b { color: #F9FAFB; }
    </style>
    """
    tooltip_js = """
        // Convert HTML string titles to DOM elements (vis.js needs this to render HTML)
        function _htmlTitle(text) {
          if (typeof text === 'string' && text.indexOf('<') > -1) {
            var div = document.createElement('div');
            div.innerHTML = text;
            return div;
          }
          return text;
        }
        nodes.get().forEach(function(n) {
          if (n.title) nodes.update({id: n.id, title: _htmlTitle(n.title)});
        });
        edges.get().forEach(function(e) {
          if (e.title) edges.update({id: e.id, title: _htmlTitle(e.title)});
        });
        """
    # Post-network-creation:
    #  - auto-fit once stabilised
    #  - disable default wheel-zoom (it traps the page scroll)
    #  - require Ctrl/Cmd + scroll to zoom (Google-Maps pattern)
    #  - show a transient hint the first time the user tries to scroll-zoom
    #    without the modifier
    post_init_js = """
        network.once("stabilizationIterationsDone", function() {
          network.fit({animation: {duration: 600, easingFunction: "easeInOutCubic"}});
        });
        network.setOptions({interaction: {zoomView: false}});

        var _netContainer = document.getElementById('mynetwork');
        _netContainer.style.position = 'relative';

        var _isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
        var _zoomHint = document.createElement('div');
        _zoomHint.style.cssText =
          'position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);' +
          'background:rgba(15,17,23,0.92); color:#F9FAFB; padding:10px 18px;' +
          'border-radius:6px; font-family:"IBM Plex Sans",sans-serif;' +
          'font-size:13px; pointer-events:none; opacity:0;' +
          'transition:opacity 0.25s; z-index:1000; white-space:nowrap;' +
          'border:1px solid #2A2D3A;';
        _zoomHint.textContent = 'Hold ' + (_isMac ? '⌘' : 'Ctrl') + ' + scroll to zoom';
        _netContainer.appendChild(_zoomHint);

        var _hintTimer = null;
        _netContainer.addEventListener('wheel', function(e) {
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            var scale = network.getScale();
            var direction = e.deltaY < 0 ? 1.1 : 1 / 1.1;
            var newScale = Math.max(0.4, Math.min(3.0, scale * direction));
            network.moveTo({scale: newScale, animation: false});
          } else {
            _zoomHint.style.opacity = '1';
            if (_hintTimer) clearTimeout(_hintTimer);
            _hintTimer = setTimeout(function() {
              _zoomHint.style.opacity = '0';
            }, 800);
          }
        }, { passive: false });
        """

    html = html.replace("</head>", tooltip_css + "</head>")
    html = html.replace(
        "network = new vis.Network(container, data, options);",
        tooltip_js
        + "\n        network = new vis.Network(container, data, options);\n"
        + post_init_js,
    )
    return html

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

/* Community card */
.community-card {
    border-radius: 8px;
    border: 1px solid #2A2D3A;
    padding: 1rem 1.1rem;
    margin-bottom: 0.5rem;
    border-left-width: 3px;
}
.community-card-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; font-weight: 600;
    letter-spacing: 0.1em; text-transform: uppercase;
    margin-bottom: 0.5rem;
}
.city-tags { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.6rem; }
.city-tag {
    display: inline-block;
    border-radius: 4px; padding: 0.12rem 0.5rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; font-weight: 600;
}

/* Callout variants */
.callout-critical {
    background: #1E0F0F; border: 1px solid #7F1D1D;
    border-left: 4px solid #EF4444; border-radius: 6px;
    padding: 0.8rem 1rem; margin: 0.75rem 0 1rem 0;
    font-size: 0.84rem; color: #FCA5A5; line-height: 1.6;
}
.callout-critical strong {
    font-family: 'IBM Plex Mono', monospace; color: #EF4444;
}
.callout-box {
    background: #1C1A0F; border: 1px solid #78350F;
    border-left: 4px solid #F59E0B; border-radius: 6px;
    padding: 0.8rem 1rem; margin-bottom: 1rem;
    font-size: 0.85rem; color: #FCD34D;
}
.callout-box strong { font-family: 'IBM Plex Mono', monospace; color: #FCD34D; }

/* Modularity badge */
.modularity-badge {
    display: inline-block;
    border-radius: 4px; padding: 0.15rem 0.55rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; font-weight: 600;
}

/* KPI mini */
.kpi-mini {
    background: #1A1D27; border: 1px solid #2A2D3A;
    border-radius: 6px; padding: 0.6rem 0.9rem;
    border-left-width: 3px;
}
.kpi-mini-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem; font-weight: 600;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: #6B7280; margin-bottom: 0.15rem;
}
.kpi-mini-value {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.3rem; font-weight: 700; color: #F9FAFB;
}

[data-testid="stDataFrame"] * { font-family: 'IBM Plex Sans', sans-serif !important; }
</style>
""", unsafe_allow_html=True)


# HEADER
st.markdown('<div class="section-label">Block 4</div>', unsafe_allow_html=True)
st.markdown("# Geographic Analysis & Community Detection")
st.markdown(
    "Territorial flow exposure and logistics community structure — "
    "identifies natural clusters, geographic dependencies and inter-cluster fragilities."
)
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def load_block4_data():
    return load_block_data("block4_geography")

with st.spinner("Running Louvain community detection..."):
    try:
        data = load_block4_data()
    except FileNotFoundError:
        st.info(
            "No analysis data is available for Geographic Analysis. "
        )
        data = {}
    except Exception:
        st.warning(
            "Geographic Analysis is currently unavailable. "
            "The page will be displayed in an empty state."
        )
        data = {}

df_city             = data.get("city_flow_exposure", pd.DataFrame())
df_country          = data.get("country_flow_exposure", pd.DataFrame())
df_louvain          = data.get("louvain_write_stats", pd.DataFrame())
df_comm             = data.get("communities_by_city", pd.DataFrame())
df_inter            = data.get("inter_community_flows", pd.DataFrame())
df_intra_summary    = data.get("intra_community_summary", pd.DataFrame())
df_intra_od_pairs   = data.get("intra_community_od_pairs", pd.DataFrame())


# PREPROCESS
# Assign stable community colours
if not df_comm.empty:
    community_ids = sorted(df_comm["community_id"].unique())
    comm_color_map = {
        cid: COMMUNITY_PALETTE[i % len(COMMUNITY_PALETTE)]
        for i, cid in enumerate(community_ids)
    }
else:
    comm_color_map = {}

# Check for single-connection communities (isolation risk)
isolated_communities = []
if not df_inter.empty:
    # Count unique inbound lanes per community
    inbound_counts = df_inter.groupby("to_community")["from_city"].nunique()
    isolated_communities = inbound_counts[inbound_counts == 1].index.tolist()

    # Also detect communities with only one outbound bridge
    outbound_counts = df_inter.groupby("from_community")["to_city"].nunique()
    single_outbound = outbound_counts[outbound_counts == 1].index.tolist()
    isolated_communities = list(set(isolated_communities + single_outbound))


# SECTION 1 - Flow Exposure

render_section_header("1 · Flow exposure per node")

toggle_col, _ = st.columns([1, 3])
with toggle_col:
    granularity = st.radio(
        "Granularity",
        options=["City", "Country"],
        horizontal=True,
        label_visibility="collapsed",
    )

if granularity == "City" and not df_city.empty:
    df_mirror = df_city.copy()
    dim_col   = "city"
    label_out = "Outbound orders"
    label_in  = "Inbound orders"
    x_title   = "Orders"
    out_col = "outbound"
    in_col  = "inbound"
elif not df_country.empty:
    df_mirror = df_country.copy()
    dim_col   = "country"
    label_out = "Outbound orders"
    label_in  = "Inbound orders"
    x_title   = "Orders"
    out_col   = "outbound"
    in_col    = "inbound"
else:
    df_mirror = pd.DataFrame()

if not df_mirror.empty and out_col in df_mirror.columns:
    df_mirror = df_mirror.copy()
    df_mirror["total"] = df_mirror[out_col] + df_mirror[in_col]
    df_mirror = df_mirror.sort_values("total", ascending=True)

    max_val = df_mirror[[out_col, in_col]].max().max()

    fig_mirror = go.Figure()

    # Left - outbound
    fig_mirror.add_trace(go.Bar(
        name=label_out,
        x=-df_mirror[out_col],
        y=df_mirror[dim_col],
        orientation="h",
        marker_color="#F59E0B",
        opacity=0.9,
        hovertemplate="<b>%{y}</b><br>Outbound: %{customdata:,}<extra></extra>",
        customdata=df_mirror[out_col],
    ))
    # Right - inbound
    fig_mirror.add_trace(go.Bar(
        name=label_in,
        x=df_mirror[in_col],
        y=df_mirror[dim_col],
        orientation="h",
        marker_color="#3B82F6",
        opacity=0.9,
        hovertemplate="<b>%{y}</b><br>Inbound: %{x:,}<extra></extra>",
    ))

    tick_step = max(1, round(max_val / 4))
    tick_vals = list(range(0, int(max_val) + tick_step, tick_step))

    fig_mirror.update_layout(
        **base_layout(height=max(280, len(df_mirror) * 40)),
        barmode="overlay",
        xaxis=dict(
            **styled_xaxis(title=x_title),
            range=[-max_val * 1.1, max_val * 1.1],
            tickvals=[-v for v in tick_vals] + tick_vals,
            ticktext=[str(v) for v in tick_vals] + [str(v) for v in tick_vals],
        ),
        yaxis=styled_yaxis(showgrid=False),
        legend=dict(
            orientation="h", y=1.08, x=0.5, xanchor="center",
            font=dict(size=10, family=FONT_SANS, color=TEXT_COLOR),
        ),
        margin=dict(l=12, r=12, t=35, b=12),
    )
    st.plotly_chart(fig_mirror, use_container_width=True)

    if granularity == "Country":
        with st.expander("Global country market share"):
            df_share = df_country[["country", "region", "pct_outbound", "pct_inbound"]].copy()
            df_share.columns = ["Country", "Region", "Export %", "Import %"]
            st.dataframe(
                df_share,
                hide_index=True, use_container_width=True,
                height=35 * len(df_share) + 37,
                column_config={
                    "Export %": st.column_config.ProgressColumn(
                        "Export %", min_value=0, max_value=100, format="%.2f%%"),
                    "Import %": st.column_config.ProgressColumn(
                        "Import %", min_value=0, max_value=100, format="%.2f%%"),
                }
            )


# SECTION 2 - Communities

st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
render_section_header("2 · Logistics communities")

# KPIs Louvain
if not df_louvain.empty:
    row_l = df_louvain.iloc[0]
    n_communities = int(row_l.get("communityCount", 0))
    modularity    = float(row_l.get("modularity_score", 0))
    nodes_written = int(row_l.get("nodePropertiesWritten", 0))

    # Modularity interpretation
    if modularity < 0.3:
        mod_label = "Weak"
    elif modularity < 0.6:
        mod_label = "Moderate"
    else:
        mod_label = "Strong"
    mod_color = "#6B7280"

    kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
    with kpi_c1:
        st.markdown(f"""
        <div class="kpi-mini" style="border-left-color:#F59E0B">
            <div class="kpi-mini-label">Comunitats detectades</div>
            <div class="kpi-mini-value">{n_communities}</div>
        </div>""", unsafe_allow_html=True)
    with kpi_c2:
        st.markdown(f"""
        <div class="kpi-mini" style="border-left-color:{mod_color}">
            <div class="kpi-mini-label">Modularity score</div>
            <div class="kpi-mini-value" style="color:{mod_color}">{modularity:.4f}</div>
        </div>""", unsafe_allow_html=True)
    with kpi_c3:
        st.markdown(f"""
        <div class="kpi-mini" style="border-left-color:#6B7280">
            <div class="kpi-mini-label">Qualitat del clustering</div>
            <div class="kpi-mini-value" style="font-size:1rem;color:{mod_color}">{mod_label}</div>
        </div>""", unsafe_allow_html=True)
    with kpi_c4:
        st.markdown(f"""
        <div class="kpi-mini" style="border-left-color:#6B7280">
            <div class="kpi-mini-label">Nodes escrits</div>
            <div class="kpi-mini-value">{nodes_written}</div>
        </div>""", unsafe_allow_html=True)

    if modularity < 0.3:
        st.markdown("""
        <div class="callout-box" style="margin-top:0.75rem">
            ⚠ <strong>Low modularity:</strong> The detected clusters are not strongly isolated from each other.
            With a synthetic dataset of 13 cities and dense flows, this is the expected result —
            the network is small and highly interconnected.
        </div>""", unsafe_allow_html=True)

st.markdown("")

# Community cards + search bar
col_cards, col_search = st.columns([2, 1])

with col_cards:
    st.markdown('<div class="section-label">Community composition</div>', unsafe_allow_html=True)
    if not df_comm.empty:
        for cid in sorted(df_comm["community_id"].unique()):
            cities = sorted(df_comm[df_comm["community_id"] == cid]["city"].tolist())
            color  = comm_color_map.get(cid, "#6B7280")
            bg_hex = color + "18"

            tags_html = "".join(
                f'<span class="city-tag" style="background:{color}22;color:{color}">{c}</span>'
                for c in cities
            )
            st.markdown(f"""
            <div class="community-card" style="border-left-color:{color};background:{bg_hex}">
                <div class="community-card-title" style="color:{color}">
                    Community {cid}
                    <span style="font-size:0.65rem;color:#6B7280;margin-left:0.5rem">
                        {len(cities)} {'city' if len(cities)==1 else 'cities'}
                    </span>
                </div>
                <div class="city-tags">{tags_html}</div>
            </div>
            """, unsafe_allow_html=True)

with col_search:
    st.markdown('<div class="section-label">Cerca de ciutat → comunitat</div>', unsafe_allow_html=True)
    search = st.text_input("", placeholder="Ex: Shanghai, Rotterdam...", label_visibility="collapsed")

    if search.strip() and not df_comm.empty:
        matches = df_comm[df_comm["city"].str.lower().str.contains(search.strip().lower())]
        if matches.empty:
            st.markdown(
                f'<div style="color:#6B7280;font-size:0.85rem;margin-top:0.5rem">'
                f'Cap resultat per "<b>{search}</b>"</div>',
                unsafe_allow_html=True,
            )
        else:
            for _, mrow in matches.iterrows():
                cid   = mrow["community_id"]
                color = comm_color_map.get(cid, "#6B7280")
                st.markdown(f"""
                <div style="background:#1A1D27;border:1px solid #2A2D3A;
                            border-left:3px solid {color};border-radius:6px;
                            padding:0.6rem 0.9rem;margin-bottom:0.4rem">
                    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.72rem;color:{color}">
                        Community {cid}
                    </div>
                    <div style="font-size:1rem;font-weight:700;color:#F9FAFB;
                                font-family:'IBM Plex Sans',sans-serif">
                        {mrow['city']}
                    </div>
                </div>""", unsafe_allow_html=True)
    elif not search.strip() and not df_comm.empty:
        # Show full membership table when no search
        st.dataframe(
            df_comm.rename(columns={"community_id": "Community", "city": "City"}),
            hide_index=True, use_container_width=True,
        )



# SECTION 3 - Inter-community dependencies

st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
render_section_header("3 · Inter-community dependencies")

bridge_lanes = []

if not df_inter.empty:
    df_inter["routes"] = df_inter["routes"].apply(
        lambda x: ", ".join(x) if isinstance(x, list) else str(x)
    )
    
    inbound_group = df_inter.groupby("to_community")

    inbound_group = df_inter.groupby("to_community")

    for comm_id, df_tmp in inbound_group:
        
        unique_edges = df_tmp[
            ["from_community", "from_city", "to_city", "routes"]
        ].copy()
        unique_edges["routes"] = unique_edges["routes"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else str(x)
        )
        unique_edges = unique_edges.drop_duplicates()

        if len(unique_edges) == 1:
            lane = unique_edges.iloc[0]

            bridge_lanes.append({
                "community": comm_id,
                "from_city": lane["from_city"],
                "to_city": lane["to_city"],
                "route": lane["routes"],
                "orders": int(df_tmp["orders"].sum()),
                "type": "single_inbound_source"
            })

    all_from = set(df_inter["from_community"])
    all_to = set(df_inter["to_community"])

    source_only = all_from - all_to

    for comm_id in source_only:
        df_tmp = df_inter[df_inter["from_community"] == comm_id].copy()
        df_tmp["routes"] = df_tmp["routes"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else str(x)
        )

        if not df_tmp.empty:
            lane = df_tmp.iloc[0]

            bridge_lanes.append({
                "community": comm_id,
                "from_city": lane["from_city"],
                "to_city": lane["to_city"],
                "route": lane["routes"],
                "orders": int(df_tmp["orders"].sum()),
                "type": "source_only"
            })

    # Critical callout
    if bridge_lanes:
        for bl in bridge_lanes:
            if bl["type"] == "single_inbound_source":
                title = f"⚠ Critical inbound dependency — Community {bl['community']}"
                body = (
                    "This community depends on a single inbound source in the network:<br>"
                    f"<span style=\"font-family:'IBM Plex Mono',monospace;color:#FCA5A5\">"
                    f"{bl['from_city']} → {bl['to_city']}</span><br>"
                    f"(Routes: {bl['route']} — {bl['orders']:,} orders).<br>"
                    "If this connection fails, the community becomes "
                    "<strong>inbound isolated</strong>."
                )
            elif bl["type"] == "source_only":
                title = f"⚠ Source node — Community {bl['community']}"
                body = (
                    "This community acts as a primary source of flow in the network.<br>"
                    "All outbound volume depends on its activity:<br>"
                    f"<span style=\"font-family:'IBM Plex Mono',monospace;color:#FCA5A5\">"
                    f"{bl['from_city']} → {bl['to_city']}</span><br>"
                    f"(Routes {bl['route']} — {bl['orders']:,} orders).<br>"
                    "If this community fails, it will "
                    "<strong>remove generated downstream flow</strong>."
                )
            else:
                continue

            st.markdown(
                f"""
                <div class="callout-critical">
                    <strong>{title}</strong><br>
                    {body}
                </div>
                """,
                unsafe_allow_html=True
            )

    # Interactive network graph (PyVis / vis.js)
    st.markdown('<div class="section-label">Network — community structure and bridges</div>', unsafe_allow_html=True)
    try:
        pyvis_html = _build_pyvis_html(
            df_comm, df_city, df_inter, df_intra_od_pairs,
            bridge_lanes, comm_color_map,
        )
        st.components.v1.html(pyvis_html, height=640, scrolling=False)
        st.caption(
            "Node color = community · Node size = total flow (inbound + outbound) · "
            "Arrows = inter-community flows, colored by the source community (width ∝ orders) · "
            "Red arrows = critical single-source dependencies · "
            "Faint grey edges = intra-community connections · "
            "Drag nodes to rearrange · Hold Ctrl/⌘ + scroll to zoom (or use the on-graph buttons) · "
            "Hover for details."
        )
    except ModuleNotFoundError:
        st.warning("PyVis is not installed. Run `pip install pyvis` to enable this view.")
    except Exception as e:
        st.error(f"Could not render network: {e}")

    # Table
    st.markdown('<div class="section-label">Bridge lanes — inter-comunitity connections</div>', unsafe_allow_html=True)

    df_bridge_display = df_inter[[
        "from_community", "to_community", "from_city", "to_city",
        "orders", "routes"
    ]].copy()

    df_bridge_display = df_bridge_display.sort_values("from_community", ascending=False)
    df_bridge_display.columns = [
        "From", "To", "From City", "To City",
        "Orders", "Routes",
    ]

    st.dataframe(
        df_bridge_display,
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("No inter-community flow data available.")
    
    
# SECTION 4 - Intra-Community Analysis

st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
render_section_header("4 · Intra-community analysis")
st.markdown(
    "Internal cohesion, risk profile and OD pairs within each logistics cluster. "
    "Select a community to inspect its structure and resilience indicators."
)

if df_intra_summary.empty or df_intra_od_pairs.empty:
    st.info("No intra-community data available.")
else:
    # Community selector
    community_options = sorted(df_intra_summary["community_id"].unique())

    sel_col, _ = st.columns([1, 3])
    with sel_col:
        selected_community = st.selectbox(
            "Select community",
            options=community_options,
            format_func=lambda x: f"Community {x}",
            label_visibility="visible",
        )

    comm_color = comm_color_map.get(selected_community, "#6B7280")

    # KPIs
    row_kpi = df_intra_summary[df_intra_summary["community_id"] == selected_community].iloc[0]

    st.markdown("")
    st.markdown(
        f'<div class="section-label" style="color:{comm_color}">Community {selected_community} — key indicators</div>',
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4= st.columns(4)

    def kpi_card(col, label, value, color, hint=""):
        col.markdown(
            f"""
            <div class="kpi-mini" style="border-left-color:{color}">
                <div class="kpi-mini-label">{label}</div>
                <div class="kpi-mini-value">{value}</div>
                {"<div style='font-family:IBM Plex Mono,monospace;font-size:0.58rem;color:#6B7280;margin-top:0.2rem'>" + hint + "</div>" if hint else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

    delay_rate   = row_kpi.get("avg_delay_rate_pct", 0)
    disrupt_rate = row_kpi.get("avg_disruption_rate_pct", 0)
    risk_score   = row_kpi.get("avg_risk_score", 0)
    route_conc   = row_kpi.get("avg_route_concentration", 0)

    # Dynamic colour thresholds
    delay_color   = "#EF4444" if delay_rate > 40 else "#F59E0B" if delay_rate > 20 else "#10B981"
    disrupt_color = "#EF4444" if disrupt_rate > 40 else "#F59E0B" if disrupt_rate > 20 else "#10B981"
    risk_color    = "#EF4444" if risk_score > 0.6 else "#F59E0B" if risk_score > 0.3 else "#10B981"
    conc_color    = "#EF4444" if route_conc > 0.7 else "#F59E0B" if route_conc > 0.4 else "#10B981"

    kpi_card(k1, "Delay rate",          f"{delay_rate:.1f}%",     delay_color,   "% delayed orders")
    kpi_card(k2, "Disruption rate",     f"{disrupt_rate:.1f}%",   disrupt_color, "% disrupted orders")
    kpi_card(k3, "Avg risk score",      f"{risk_score:.3f}",      risk_color,    "risk — 1 = critical")
    kpi_card(k4, "Route concentration", f"{route_conc:.3f}",      conc_color,    "HHI — 1 = single route")

    # OD pairs table
    st.markdown("")
    st.markdown(
        f'<div class="section-label" style="color:{comm_color}">Internal OD pairs</div>',
        unsafe_allow_html=True,
    )

    df_od = df_intra_od_pairs[df_intra_od_pairs["community_id"] == selected_community].copy()
    df_od = df_od.drop(columns=["community_id"], errors="ignore")

    if "routes_used" in df_od.columns:
        df_od["routes_used"] = df_od["routes_used"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else str(x)
        )

    df_od_display = df_od.rename(columns={
        "origin":               "Origin",
        "destination":          "Destination",
        "orders":               "Orders",
        "routes_used":          "Routes used",
        "delay_rate_pct":       "Delay rate %",
        "disruption_rate_pct":  "Disruption rate %",
        "route_concentration":  "Route concentration",
    })

    if df_od_display.empty:
        st.info("No OD pairs available for this community.")
    else:
        st.dataframe(
            df_od_display,
            hide_index=True,
            use_container_width=True,
            height=min(34 * (len(df_od_display) + 1) + 10, 420),
            column_config={
                "Orders": st.column_config.NumberColumn("Orders", format="%d"),
                "Delay rate %": st.column_config.ProgressColumn(
                    "Delay rate %", min_value=0, max_value=100, format="%.1f%%"
                ),
                "Disruption rate %": st.column_config.ProgressColumn(
                    "Disruption rate %", min_value=0, max_value=100, format="%.1f%%"
                ),
                "Route concentration": st.column_config.ProgressColumn(
                    "Route concentration", min_value=0, max_value=1, format="%.3f"
                ),
            },
    )

    st.caption(
        "Route concentration (HHI): 1.0 = single route dependency · "
        "Delay rate: % of orders arriving late within this OD pair."
    )