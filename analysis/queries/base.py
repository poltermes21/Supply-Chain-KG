"""
Shared utilities for executing Neo4j queries across multiple analysis modules.
"""

import pandas as pd
from neo4j import GraphDatabase


def get_driver(uri: str, user: str, password: str):
    """Retorna un driver Neo4j connectat."""
    return GraphDatabase.driver(uri, auth=(user, password))


def run_query(driver, cypher: str, params: dict = None) -> pd.DataFrame:
    """Executa una consulta Cypher i retorna un DataFrame."""
    with driver.session() as session:
        result = session.run(cypher, params or {})
        return pd.DataFrame([r.data() for r in result])