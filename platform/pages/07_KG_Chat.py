"""
platform/pages/07_KG_Chat.py
Natural-language chat interface for the supply-chain Knowledge Graph.
Adapted for the ReAct agent: uses agent.run(), supports multi-query Cypher audit.
"""

import streamlit as st
import uuid
from agent import run as agent_run, get_memory

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="KG Chat", layout="wide")

# ─────────────────────────────────────────────
# SHARED STYLE
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

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

SESSION_ID = st.session_state.session_id

if "show_cypher" not in st.session_state:
    st.session_state.show_cypher = False

if "pending_input" not in st.session_state:
    st.session_state.pending_input = None

# Chat display history — list of dicts with role, content, cypher_queries, iterations
if "display_history" not in st.session_state:
    st.session_state.display_history = []

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">Block 7</div>', unsafe_allow_html=True)
st.markdown("# 💬 Knowledge Graph Chat")
st.markdown(
    "Ask questions in natural language — the agent translates them to Cypher, "
    "queries the Neo4j graph, and returns a grounded answer."
)
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
is_generating = st.session_state.pending_input is not None

with st.sidebar:
    st.markdown("### ⚙️ Chat settings")

    st.toggle(
        "Show generated Cypher",
        key="show_cypher",
        disabled=is_generating,
    )

    if st.button(
        "🗑️ Clear conversation",
        use_container_width=True,
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

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def render_user_msg(content: str) -> None:
    st.markdown(
        f'<div class="msg-user">'
        f'<div class="msg-label msg-label-user">You</div>'
        f'{content}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_assistant_msg(
    content: str,
    cypher_queries: list[str] | None = None,
    iterations: int = 0,
) -> None:
    iter_badge = (
        f'<span class="iter-badge">{iterations} tool call{"s" if iterations != 1 else ""}</span>'
        if iterations > 0 else ""
    )
    st.markdown(
        f'<div class="msg-assistant">'
        f'<div class="msg-label msg-label-assistant">Agent{iter_badge}</div>'
        f'{content}'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.session_state.show_cypher and cypher_queries:
        for i, cypher in enumerate(cypher_queries):
            label = f"Cypher Query {i + 1}" if len(cypher_queries) > 1 else "Cypher Query"
            with st.expander(label):
                st.code(cypher, language="cypher")

# ─────────────────────────────────────────────
# CHAT HISTORY DISPLAY
# ─────────────────────────────────────────────
if not st.session_state.display_history and not is_generating:
    st.markdown(
        '<div style="color:#4B5563; font-style:italic; padding:1rem 0;">'
        "No messages yet. Ask something about your supply-chain graph ↓"
        "</div>",
        unsafe_allow_html=True,
    )

for msg in st.session_state.display_history:
    if msg["role"] == "user":
        render_user_msg(msg["content"])
    else:
        render_assistant_msg(
            msg["content"],
            cypher_queries=msg.get("cypher_queries"),
            iterations=msg.get("iterations", 0),
        )

# ─────────────────────────────────────────────
# PROCESS PENDING INPUT
# ─────────────────────────────────────────────
if st.session_state.pending_input:
    question = st.session_state.pending_input

    # Show the user message immediately
    render_user_msg(question)

    with st.spinner("Thinking..."):
        try:
            result = agent_run(question, session_id=SESSION_ID)
            answer         = result.answer
            cypher_queries = result.cypher_queries   # list[str], one per tool call
            iterations     = result.iterations_used
        except Exception as e:
            answer         = f"Agent error: {e}"
            cypher_queries = []
            iterations     = 0

    # Persist to display history
    st.session_state.display_history.append({"role": "user", "content": question})
    st.session_state.display_history.append({
        "role":          "assistant",
        "content":       answer,
        "cypher_queries": cypher_queries,
        "iterations":    iterations,
    })

    st.session_state.pending_input = None
    st.rerun()

# ─────────────────────────────────────────────
# INPUT — st.chat_input (disabled natively while page reruns)
# ─────────────────────────────────────────────
# st.chat_input is automatically non-interactive while Streamlit is
# processing a rerun, which gives us the "blocked while thinking" behaviour
# without any manual disabled= flag.
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

user_input = st.chat_input(
    placeholder="e.g. Which routes have the highest disruption rate?",
    disabled=is_generating,   # extra safety: also disable if pending
    key="chat_input",
)

if user_input and user_input.strip() and not is_generating:
    st.session_state.pending_input = user_input.strip()
    st.rerun()