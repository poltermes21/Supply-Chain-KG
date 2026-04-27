"""
platform/pages/07_KG_Chat.py
Natural-language chat interface for the supply-chain Knowledge Graph.
"""

import streamlit as st
from agent import kg_agent, ConversationMemory

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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()

if "show_cypher" not in st.session_state:
    st.session_state.show_cypher = False

if "is_generating" not in st.session_state:
    st.session_state.is_generating = False

if "pending_input" not in st.session_state:
    st.session_state.pending_input = None

memory: ConversationMemory = st.session_state.memory

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
with st.sidebar:
    st.markdown("### ⚙️ Chat settings")

    st.toggle(
        "Show generated Cypher",
        key="show_cypher",
        disabled=st.session_state.is_generating,
    )

    if st.button(
        "🗑️ Clear conversation",
        use_container_width=True,
        disabled=st.session_state.is_generating,
    ):
        memory.clear()
        st.session_state.pending_input = None
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

def render_assistant_msg(content: str, cypher: str | None = None) -> None:
    st.markdown(
        f'<div class="msg-assistant">'
        f'<div class="msg-label msg-label-assistant">Agent</div>'
        f'{content}'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.session_state.show_cypher and cypher:
        with st.expander("Cypher Query"):
            st.code(cypher, language="cypher")

# ─────────────────────────────────────────────
# CHAT HISTORY DISPLAY
# ─────────────────────────────────────────────
if not memory.messages and not st.session_state.pending_input:
    st.markdown(
        '<div style="color:#4B5563; font-style:italic; padding:1rem 0;">'
        "No messages yet. Ask something about your supply-chain graph ↓"
        "</div>",
        unsafe_allow_html=True,
    )

for msg in memory.messages:
    if msg["role"] == "user":
        render_user_msg(msg["content"])
    else:
        render_assistant_msg(msg["content"], cypher=msg.get("cypher"))

if st.session_state.pending_input:
    render_user_msg(st.session_state.pending_input)
    memory.add_user(st.session_state.pending_input)

    with st.spinner("Thinking..."):
        question = st.session_state.pending_input
        initial_state = {
            "question":          question,
            "chat_history":      memory.get_history(),
            "intent":            None,
            "entities":          [],
            "cypher_query":      None,
            "generation_prompt": None,
            "validation_ok":     False,
            "validation_error":  None,
            "raw_results":       [],
            "execution_error":   None,
            "retry_count":       0,
            "retry_feedback":    None,
            "answer":            None,
            "is_followup":       False,
        }
        try:
            final_state = kg_agent.invoke(initial_state)
            answer      = final_state.get("answer") or "No answer generated."
            cypher      = final_state.get("cypher_query")
        except Exception as e:
            answer = f"Agent error: {e}"
            cypher = None

    memory.add_assistant(answer, cypher=cypher)
    st.session_state.pending_input = None
    st.session_state.is_generating = False
    st.rerun()

# ─────────────────────────────────────────────
# INPUT FORM
# ─────────────────────────────────────────────
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

if st.session_state.is_generating:
    st.text_input(
        "Your question",
        placeholder="Agent is thinking...",
        label_visibility="collapsed",
        disabled=True,
        key="input_disabled",
    )
else:
    with st.form("chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([9, 1])
        with col_input:
            user_input = st.text_input(
                "Your question",
                placeholder="e.g. Which routes have the highest disruption rate?",
                label_visibility="collapsed",
            )
        with col_btn:
            submitted = st.form_submit_button("Send", use_container_width=True)

    if submitted and user_input.strip():
        st.session_state.pending_input = user_input.strip()
        st.session_state.is_generating = True
        st.rerun()