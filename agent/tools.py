"""
agent/tools.py
The three tools available to the ReAct agent.

query_graph        — generate + validate + execute a Cypher query
get_entity_details — fetch full details for a known entity ID
answer_from_context — signal that no new query is needed (context is enough)

All tools are read-only. The validator runs inside every tool that touches Neo4j,
acting as a hard firewall independent of the LLM's behaviour.
"""

import re
import json
from typing import Any

from langchain_core.tools import tool
from connection import get_neo4j_driver

# ─────────────────────────────────────────────────────────────────────────────
# Security: static validator (shared by both Neo4j tools)
# ─────────────────────────────────────────────────────────────────────────────

_WRITE_RE = re.compile(
    r"\b(MERGE|CREATE|DELETE|DETACH\s+DELETE|SET|REMOVE|DROP)\b",
    re.IGNORECASE,
)

_ALLOWED_APOC = {
    "apoc.algo.dijkstra",
    "apoc.algo.astar",
    "apoc.path.expand",
    "apoc.path.subgraphNodes",
}

_APOC_CALL_RE = re.compile(r"CALL\s+(apoc\.[a-zA-Z.]+)", re.IGNORECASE)

_ALLOWED_LABELS = {
    "Order", "RiskAssessment", "City", "Country", "Route",
    "ProductCategory", "TransportMode", "DisruptionType", "MitigationAction",
}

_ALLOWED_RELS = {
    "HAS_RISK", "ORIGIN_FROM", "DESTINATION_TO", "SHIPPED_VIA",
    "TRANSPORTS", "USES_MODE", "AFFECTED_BY", "MITIGATED_WITH",
    "CONNECTS", "VULNERABLE_TO", "LOCATED_IN", "CITY_FLOW",
}

_LABEL_RE = re.compile(r"\([^)]+:([A-Za-z][A-Za-z0-9_]*)")
_REL_RE = re.compile(r"\[[^\]]*:([A-Z_][A-Z0-9_]*)")

_MAX_RECORDS = 30   # observation size cap — keeps ReAct context bounded


def _validate(cypher: str) -> None:
    """Raise ValueError with a descriptive message if the query is unsafe."""

    # 1. Write operations
    bad = _WRITE_RE.findall(cypher)
    if bad:
        ops = ", ".join(sorted({m.strip().upper() for m in bad}))
        raise ValueError(f"Forbidden write operation(s): {ops}. Only READ queries allowed.")

    # 2. APOC whitelist
    for proc in _APOC_CALL_RE.findall(cypher):
        if proc.lower() not in {p.lower() for p in _ALLOWED_APOC}:
            raise ValueError(
                f"APOC procedure '{proc}' is not whitelisted. "
                f"Allowed: {', '.join(sorted(_ALLOWED_APOC))}"
            )

    # 3. Must have MATCH
    if "MATCH" not in cypher.upper():
        raise ValueError("Query must contain at least one MATCH clause.")

    # 4. Must have LIMIT
    if "LIMIT" not in cypher.upper():
        raise ValueError("Query must include a LIMIT clause (max 30 recommended).")

    # 5. Unknown node labels
    unknown_labels = set(_LABEL_RE.findall(cypher)) - _ALLOWED_LABELS
    if unknown_labels:
        raise ValueError(
            f"Unknown node label(s): {', '.join(sorted(unknown_labels))}. "
            f"Allowed: {', '.join(sorted(_ALLOWED_LABELS))}"
        )

    # 6. Unknown relationship types
    unknown_rels = set(_REL_RE.findall(cypher)) - _ALLOWED_RELS
    if unknown_rels:
        raise ValueError(
            f"Unknown relationship type(s): {', '.join(sorted(unknown_rels))}. "
            f"Allowed: {', '.join(sorted(_ALLOWED_RELS))}"
        )


def _run_read(cypher: str, params: dict | None = None) -> list[dict]:
    """Execute a validated Cypher query inside a READ transaction."""
    driver = get_neo4j_driver()

    def _tx(tx):
        result = tx.run(cypher, **(params or {}))
        return [dict(r) for r in result][:_MAX_RECORDS]

    with driver.session() as session:
        return session.execute_read(_tx)


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1 — query_graph
# ─────────────────────────────────────────────────────────────────────────────

@tool
def query_graph(cypher: str) -> str:
    """
    Execute a read-only Cypher query against the supply chain Neo4j knowledge graph.

    Use this tool to answer questions that require fetching data:
    aggregations, filters, rankings, path queries, etc.

    The query MUST be read-only (no MERGE, CREATE, DELETE, SET).
    Always include a LIMIT clause.
    Use only node labels and relationship types defined in the schema.

    Returns a JSON-serialised list of records (max 30).
    If the query is invalid or unsafe, returns an error string starting with 'ERROR:'.
    """
    try:
        _validate(cypher)
        records = _run_read(cypher)
        if not records:
            return "No records returned. The query ran successfully but matched nothing."
        return json.dumps(records, indent=2, default=str)
    except ValueError as e:
        return f"ERROR (validation): {e}"
    except Exception as e:
        return f"ERROR (execution): {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2 — answer_from_context
# ─────────────────────────────────────────────────────────────────────────────

@tool
def answer_from_context(reasoning: str) -> str:
    """
    Use this tool when you can answer the user's question using ONLY the
    information already present in the conversation history — without querying
    the database again.

    Examples of when to use this:
    - "What does that percentage mean?"
    - "Which of the routes you listed has the lowest frequency?"
    - "Summarise what we've discussed so far."
    - Any clarification or explanation of data already returned.

    Pass your reasoning/answer as the 'reasoning' argument.
    The content will be returned directly to the user.
    """
    return reasoning