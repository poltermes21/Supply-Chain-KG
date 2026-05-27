"""
platform/pages/07_KG_Chat.py
Natural-language chat interface for the supply-chain Knowledge Graph.
Adapted for the ReAct agent: uses agent.run(), supports multi-query Cypher audit.
"""

import streamlit as st
import uuid
import re
import markdown as md_lib
import plotly.express as px
from agent import run as agent_run, get_memory, generate_chart_specs

st.set_page_config(page_title="KG Chat", layout="wide")

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

.msg-user {
    background: #1E2433;
    border-left: 3px solid #3B82F6;
    border-radius: 0 8px 8px 0;
    padding: 0.7rem 1rem;
    margin: 0.5rem 0;
    font-size: 0.95rem;
}
.msg-assistant {
    background: #1A1D27;
    border-left: 3px solid #F59E0B;
    border-radius: 0 8px 8px 0;
    padding: 0.7rem 1rem;
    margin: 0.5rem 0;
    font-size: 0.95rem;
}
.msg-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}
.msg-label-user      { color: #3B82F6; }
.msg-label-assistant { color: #F59E0B; }

[data-testid="stExpander"] {
    background: #111827 !important;
    border: 1px solid #2A2D3A !important;
    border-radius: 6px !important;
    margin-top: 0.5rem !important;
}
[data-testid="stExpander"] summary {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important;
    color: #6B7280 !important;
    letter-spacing: 0.08em !important;
}

.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.67rem; font-weight: 600;
    letter-spacing: 0.14em; text-transform: uppercase;
    color: #6B7280; margin-bottom: 0.3rem;
}
.divider-line {
    border: none; border-top: 1px solid #2A2D3A; margin: 1.25rem 0;
}

/* Subtle iteration badge */
.iter-badge {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.58rem;
    color: #6B7280;
    border: 1px solid #2A2D3A;
    border-radius: 4px;
    padding: 1px 6px;
    margin-left: 0.5rem;
    vertical-align: middle;
}
</style>
""", unsafe_allow_html=True)

# SESSION STATE
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

SESSION_ID = st.session_state.session_id

if "show_cypher" not in st.session_state:
    st.session_state.show_cypher = False

if "pending_input" not in st.session_state:
    st.session_state.pending_input = None

if "pending_chart_idx" not in st.session_state:
    st.session_state.pending_chart_idx = None

if "display_history" not in st.session_state:
    st.session_state.display_history = []


# HEADER
st.markdown('<div class="section-label">Block 7</div>', unsafe_allow_html=True)
st.markdown("# Knowledge Graph Chat")
st.markdown(
    "Ask questions in natural language — the agent translates them to Cypher, "
    "queries the Neo4j graph, and returns a grounded answer."
)
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

# SIDEBAR
# Lock all state-mutating controls while EITHER an answer or a chart is
# generating, so the user can't fire a second operation in parallel.
is_generating = (
    st.session_state.pending_input is not None
    or st.session_state.pending_chart_idx is not None
)

with st.sidebar:
    st.markdown("### Chat settings")

    st.toggle(
        "Show generated Cypher",
        key="show_cypher",
        disabled=is_generating,
    )

    if st.button(
        "🗑️ Clear conversation",
        width='stretch',
        disabled=is_generating,
    ):
        st.session_state.display_history = []
        st.session_state.pending_input = None
        get_memory(SESSION_ID).clear()
        st.rerun()

    st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
    st.markdown("**Example questions**")
    for s in [
        "Which routes have the highest delay rate?",
        "What are the top 5 origin cities by orders volume?",
        "How does air compare to sea in average cost?",
        "Which products are most affected by disruptions?",
        "Show me the most concentrated OD lanes.",
        "What is the average lead time for Suez route orders?",
    ]:
        st.caption(f"• {s}")

# HELPERS
def md_to_html(text: str) -> str:
    # Normalize bullets
    text = re.sub(r'(?m)^\*\s+', '- ', text)
    return md_lib.markdown(
        text,
        extensions=["nl2br", "tables"],
    )

def render_user_msg(content: str) -> None:
    st.markdown(
        f'<div class="msg-user">'
        f'<div class="msg-label msg-label-user">You</div>'
        f'{md_to_html(content)}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_chart(spec, dataframes) -> None:
    """Render one ChartSpec via plotly.express."""
    if spec.df_index < 0 or spec.df_index >= len(dataframes):
        return
    df = dataframes[spec.df_index]
    if df is None or df.empty:
        return
    try:
        kwargs = {"title": spec.title}
        if spec.color_col:
            kwargs["color"] = spec.color_col
        if spec.chart_type == "bar":
            fig = px.bar(df, x=spec.x_col, y=spec.y_col, **kwargs)
        elif spec.chart_type == "line":
            fig = px.line(df, x=spec.x_col, y=spec.y_col, markers=True, **kwargs)
        elif spec.chart_type == "scatter":
            fig = px.scatter(df, x=spec.x_col, y=spec.y_col, **kwargs)
        elif spec.chart_type == "pie":
            fig = px.pie(df, names=spec.x_col, values=spec.y_col, title=spec.title)
        else:
            return
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Sans, sans-serif", color="#E5E7EB"),
            margin=dict(l=10, r=10, t=40, b=40),
            height=360,
        )
        st.plotly_chart(fig, width="stretch")
        if spec.rationale:
            st.caption(spec.rationale)
    except Exception as e:
        st.warning(f"Could not render chart: {e}")


def render_assistant_msg(
    content: str,
    cypher_queries: list[str] | None = None,
    iterations: int = 0,
    msg_idx: int | None = None,
    chartable: bool = False,
    charts: list | None = None,
    tool_dataframes: list | None = None,
    question: str = "",
    chart_error: str | None = None,
) -> None:
    iter_badge = (
        f'<span class="iter-badge">{iterations} tool call{"s" if iterations != 1 else ""}</span>'
        if iterations > 0 else ""
    )
    st.markdown(
        f'<div class="msg-assistant">'
        f'<div class="msg-label msg-label-assistant">Agent{iter_badge}</div>'
        f'{md_to_html(content)}'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.session_state.show_cypher and cypher_queries:
        for i, cypher in enumerate(cypher_queries):
            label = f"Cypher Query {i + 1}" if len(cypher_queries) > 1 else "Cypher Query"
            with st.expander(label):
                st.code(cypher, language="cypher")

    if not (chartable and msg_idx is not None and tool_dataframes):
        return

    is_generating_this = st.session_state.pending_chart_idx == msg_idx
    any_op_in_progress = (
        st.session_state.pending_input is not None
        or st.session_state.pending_chart_idx is not None
    )

    if is_generating_this:
        # The Flash call for this message is running right now — show inline
        # progress so the user knows where the work is happening.
        st.caption("Generating visualisation…")
    elif chart_error:
        # Distinguishes a real failure from "Flash returned no charts".
        st.warning(f"Could not generate visualisation. {chart_error}")
        if st.button(
            "Try again",
            key=f"viz_retry_{msg_idx}",
            disabled=any_op_in_progress,
        ):
            st.session_state.display_history[msg_idx]["chart_error"] = None
            st.session_state.pending_chart_idx = msg_idx
            st.rerun()
    elif charts is None:
        # Not yet generated — surface the on-demand button.
        if st.button(
            "Visualize",
            key=f"viz_btn_{msg_idx}",
            disabled=any_op_in_progress,
        ):
            st.session_state.pending_chart_idx = msg_idx
            st.rerun()
    elif len(charts) == 0:
        st.caption("No additional visualisation adds insight for this answer.")
    else:
        for spec in charts:
            _render_chart(spec, tool_dataframes)

# CHAT HISTORY DISPLAY
if not st.session_state.display_history and not is_generating:
    st.markdown(
        '<div style="color:#4B5563; font-style:italic; padding:1rem 0;">'
        "No messages yet. Ask something about your supply-chain graph ↓"
        "</div>",
        unsafe_allow_html=True,
    )

def _previous_user_question(history, idx):
    """Walk backwards from `idx` and return the latest user message content."""
    for j in range(idx - 1, -1, -1):
        m = history[j]
        if m.get("role") == "user":
            return m.get("content", "")
    return ""

for i, msg in enumerate(st.session_state.display_history):
    if msg["role"] == "user":
        render_user_msg(msg["content"])
    else:
        render_assistant_msg(
            msg["content"],
            cypher_queries=msg.get("cypher_queries"),
            iterations=msg.get("iterations", 0),
            msg_idx=i,
            chartable=msg.get("chartable", False),
            charts=msg.get("charts"),  # None = not yet generated, [] = generated but empty
            tool_dataframes=msg.get("tool_dataframes"),
            question=_previous_user_question(st.session_state.display_history, i),
            chart_error=msg.get("chart_error"),
        )


# PROCESS PENDING INPUT
if st.session_state.pending_input:
    question = st.session_state.pending_input

    # Show the user message immediately
    render_user_msg(question)

    with st.spinner("Thinking..."):
        try:
            result = agent_run(question, session_id=SESSION_ID)
            answer          = result.answer
            cypher_queries  = result.cypher_queries
            iterations      = result.iterations_used
            tool_dataframes = result.tool_dataframes
            chartable       = result.chartable
        except Exception as e:
            answer          = f"Agent error: {e}"
            cypher_queries  = []
            iterations      = 0
            tool_dataframes = []
            chartable       = False

    # Persist to display history
    st.session_state.display_history.append({"role": "user", "content": question})
    st.session_state.display_history.append({
        "role":            "assistant",
        "content":         answer,
        "cypher_queries":  cypher_queries,
        "iterations":      iterations,
        "tool_dataframes": tool_dataframes,
        "chartable":       chartable,
        "charts":          None,  # not yet generated; the Visualize button drives this
        "chart_error":     None,  # populated only if chart generation throws
    })

    st.session_state.pending_input = None
    st.rerun()


# PROCESS PENDING CHART REQUEST
if st.session_state.pending_chart_idx is not None:
    idx = st.session_state.pending_chart_idx
    history = st.session_state.display_history
    if 0 <= idx < len(history) and history[idx].get("role") == "assistant":
        entry = history[idx]
        question = _previous_user_question(history, idx)
        try:
            with st.spinner("Generating charts..."):
                specs = generate_chart_specs(
                    question=question,
                    dataframes=entry.get("tool_dataframes") or [],
                    answer=entry.get("content", ""),
                )
            # Success: store specs (possibly empty if Flash said no chart helps),
            # clear any prior error.
            entry["charts"]      = specs
            entry["chart_error"] = None
        except Exception as e:
            # Real failure: keep `charts` as None so the user can retry, and
            # surface a short reason inline next to the message.
            err_msg = str(e) or e.__class__.__name__
            if len(err_msg) > 200:
                err_msg = err_msg[:200] + "…"
            entry["charts"]      = None
            entry["chart_error"] = err_msg
    st.session_state.pending_chart_idx = None
    st.rerun()

# INPUT
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

user_input = st.chat_input(
    placeholder="e.g. Which routes have the highest disruption rate?",
    disabled=is_generating,
    key="chat_input",
)

if user_input and user_input.strip() and not is_generating:
    st.session_state.pending_input = user_input.strip()
    st.rerun()