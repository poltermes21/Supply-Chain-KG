from analysis.queries.base import get_driver
from settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def get_neo4j_driver():
    """
    Creates a Neo4j driver instance.
    - Inside Streamlit: uses st.secrets + st.cache_resource
    - Outside Streamlit (tests, CLI): uses settings.py / .env
    """
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is None:
            raise RuntimeError("Not in Streamlit context")

        @st.cache_resource
        def _cached_driver():
            uri      = st.secrets["NEO4J_URI"]
            user     = st.secrets["NEO4J_USER"]
            password = st.secrets["NEO4J_PASSWORD"]
            return get_driver(uri, user, password)

        return _cached_driver()

    except Exception:
        return get_driver(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)