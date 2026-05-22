import streamlit as st

from shared.documentation_content import DOCUMENTATION_PAGES

st.set_page_config(page_title="Documentation", layout="wide")

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
p, li, span, label, div { color: #E5E7EB; font-family: 'IBM Plex Sans', sans-serif; }
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
    margin-bottom: 0.5rem;
    border-left: 3px solid #F59E0B; padding-left: 0.75rem;
    line-height: 1.3;
}
.divider-line {
    border: none; border-top: 1px solid #2A2D3A; margin: 1.5rem 0;
}
.doc-card {
    background: #1A1D27;
    border: 1px solid #2A2D3A;
    border-radius: 10px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.9rem;
}
.doc-card-title {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1rem; font-weight: 700; color: #F9FAFB;
    margin-bottom: 0.35rem;
}
.doc-card-summary {
    color: #D1D5DB;
    line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="section-label">Platform guide</div>', unsafe_allow_html=True)
st.markdown("# Documentation")
st.markdown(
    "A brief guide to the platform sections. Use it to understand what each block shows before exploring the charts and tables."
)
st.info("Tip: every page includes ℹ help buttons beside section headers. Click them anytime to open quick explanations for that section.")
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

for page in DOCUMENTATION_PAGES:
    st.markdown(f'### {page["page_title"]}')
    st.caption(page["summary"])
    with st.expander("Section guide", expanded=False):
        if page["sections"]:
            for section in page["sections"]:
                st.markdown(f'**{section["title"]}**')
                st.caption(section["summary"])

