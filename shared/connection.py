import streamlit as st
import sys
import os

from analysis.queriesv2.base import get_driver

@st.cache_resource
def get_neo4j_driver():
    """
    Creates and caches a single Neo4j driver instance.
    The driver is shared across all app pages and the AI agent to optimize performance.
    """
    try:
        uri = st.secrets["NEO4J_URI"]
        user = st.secrets["NEO4J_USER"]
        password = st.secrets["NEO4J_PASSWORD"]
        
        driver = get_driver(uri, user, password)
        return driver
    except Exception as e:
        st.error(f"Critical Error: Could not connect to Neo4j. {e}")
        st.stop()