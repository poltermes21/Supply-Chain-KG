"""
agent/nodes.py
One function per LangGraph node.
"""

import re
import json
from typing import Any

from .state import AgentState
from .schema import KG_SCHEMA_PROMPT
from .llm import get_interface_llm, get_reasoning_llm
from connection import get_neo4j_driver

# ─────────────────────────────────────────────
# 1. Intent detection
# ─────────────────────────────────────────────

INTENT_SYSTEM = """You are an intent classifier for a supply-chain knowledge graph.
Given a user question, return a JSON object with:
  - "intent": one of [route_query, hub_analysis, disruption_query, cost_query, 
                       product_query, geographic_query, general_stats, unknown]
  - "entities": list of proper nouns or named entities mentioned (cities, routes, products…)

Respond ONLY with valid JSON, no markdown.
"""

def detect_intent(state: AgentState) -> AgentState:
    llm   = get_interface_llm(temperature=0)
    reply = llm.invoke([
        {"role": "system",  "content": INTENT_SYSTEM},
        {"role": "user",    "content": state.question},
    ])
    try:
        parsed = json.loads(reply.content)
    except Exception:
        parsed = {"intent": "unknown", "entities": []}

    return state.model_copy(update={
        "intent": parsed.get("intent", "unknown"),
        "entities": parsed.get("entities", []),
    })

# ─────────────────────────────────────────────
# 2. Cypher generation
# ─────────────────────────────────────────────

GENERATE_SYSTEM = f"""You are a Neo4j Cypher expert.
You will receive a natural-language question about a supply-chain knowledge graph.
Use ONLY the schema below to write a valid, read-only Cypher query.

{KG_SCHEMA_PROMPT}

### RULES:
- NEVER use MERGE, CREATE, DELETE, SET, or any write operation.
- ALWAYS add a LIMIT clause (default 50).
- Use only node labels and relationship types defined in the schema.
- Return column names in snake_case.
- Respond with ONLY the raw Cypher query — no markdown, no explanation.
"""

def generate_query(state: AgentState) -> AgentState:
    llm = get_reasoning_llm(temperature=0)

    history_str = ""
    for msg in (state.chat_history)[-4:]:   # last 2 turns
        history_str += f"{msg['role'].capitalize()}: {msg['content']}\n"

    user_prompt = (
        f"{history_str}\nQuestion: {state.question}\n"
        f"Detected intent: {state.intent or 'unknown'}\n"
        f"Key entities: {', '.join(state.entities)}"
    )

    reply = llm.invoke([
        {"role": "system", "content": GENERATE_SYSTEM},
        {"role": "user",   "content": user_prompt},
    ])

    query = reply.content.strip().strip("```").strip()

    return state.model_copy(update={
        "cypher_query": query,
        "generation_prompt": user_prompt,
        "validation_ok": False,
        "validation_error":  None,
        "execution_error":   None,
    })

# ─────────────────────────────────────────────
# 3. Validator
# ─────────────────────────────────────────────

_WRITE_KEYWORDS = re.compile(
    r"\b(MERGE|CREATE|DELETE|DETACH|SET|REMOVE|DROP|CALL\s+apoc\.periodic)\b",
    re.IGNORECASE,
)

_ALLOWED_LABELS = {
    "Order",
    "RiskAssessment",
    "City",
    "Country",
    "Route",
    "ProductCategory",
    "TransportMode",
    "DisruptionType",
    "MitigationAction",
}

_ALLOWED_REL_TYPES = {
    "HAS_RISK",
    "ORIGIN_FROM",
    "DESTINATION_TO",
    "SHIPPED_VIA",
    "TRANSPORTS",
    "USES_MODE",
    "AFFECTED_BY",
    "MITIGATED_WITH",
    "CONNECTS",
    "VULNERABLE_TO",
    "LOCATED_IN",
    "CITY_FLOW",
}

def validate_query(state: AgentState) -> AgentState:
    query = state.cypher_query or None
    
    # 1 — No query generated (LLM failure)
    if query is None:
        return state.model_copy(update={
            "validation_ok": False,
            "validation_error": "LLM did not generate a Cypher query.",
        })
        
    # 2 — Safety: no write operations
    matches = _WRITE_KEYWORDS.findall(query)
    if matches:
        operations = sorted(set(m.strip().upper() for m in matches))
        return state.model_copy(update={
            "validation_ok": False,
            "validation_error": f"Query contains forbidden write operations: {', '.join(operations)}. Only read-only queries are allowed."
        })
    
    # 3 — Must have MATCH
    if "MATCH" not in query.upper():
        return state.model_copy(update={
            "validation_ok": False,
            "validation_error": "Query must contain at least one MATCH clause."
        })

    # 4 — Must have LIMIT
    if "LIMIT" not in query.upper():
        return state.model_copy(update={
            "validation_ok": False,
            "validation_error": "Query must include a LIMIT clause."
        })

    return state.model_copy(update={
        "validation_ok": True, 
        "validation_error": None
    })

# ─────────────────────────────────────────────
# 4. Execution
# ─────────────────────────────────────────────

def execute_query(state: AgentState) -> AgentState:
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result  = session.run(state.cypher_query)
            records = [dict(r) for r in result]
        return state.model_copy(update={
            "raw_results": records,
            "execution_error": None
        })
    except Exception as e:
        return state.model_copy(update={
            "raw_results": [],
            "execution_error": str(e)
        })

# ─────────────────────────────────────────────
# 5. Regenerate (retry with feedback)
# ─────────────────────────────────────────────

REGEN_SYSTEM = f"""You are a Neo4j Cypher expert fixing a broken query.
You will receive the original question, the faulty query, and the error message.
Rewrite the query so it is correct and follows all the rules below.

{KG_SCHEMA_PROMPT}

### RULES:
- NEVER use MERGE, CREATE, DELETE, SET, or any write operation.
- ALWAYS add a LIMIT clause (default 50).
- Use only node labels and relationship types defined in the schema.
- Return column names in snake_case.
- Respond with ONLY the raw Cypher query — no markdown, no explanation.
"""

def regenerate_query(state: AgentState) -> AgentState:
    llm = get_reasoning_llm(temperature=0.2)   # slight temperature for variation

    feedback = state.validation_error or state.execution_error or "Unknown error"

    user_prompt = (
        f"Original question: {state.question}\n\n"
        f"Faulty Cypher query:\n{state.cypher_query or ''}\n\n"
        f"Error / reason for failure:\n{feedback}"
    )

    reply = llm.invoke([
        {"role": "system", "content": REGEN_SYSTEM},
        {"role": "user",   "content": user_prompt},
    ])

    new_query = reply.content.strip().strip("```").strip()

    return state.model_copy(update={
        "cypher_query":     new_query,
        "retry_count":      state.retry_count + 1,
        "retry_feedback":   feedback,
        "validation_ok":    False,
        "validation_error": None,
        "execution_error":  None,
    })

# ─────────────────────────────────────────────
# 6. LLM Formatter
# ─────────────────────────────────────────────

FORMAT_SYSTEM = """You are a supply-chain analyst assistant.
### CORE RULES:
1. LANGUAGE: Always respond in the same language used by the user in their last question.
2. SOURCE: Answer using ONLY the data provided below.
3. INTEGRITY: Do NOT invent numbers, names, or facts not present in the data. 
4. NO DATA: If no data was returned from the database, state it clearly in the user's language.

### STYLE GUIDELINES:
- Be concise and factual.
- Use bullet points or a short table for lists or comparisons.
- Maintain a professional, analytical tone.
"""

def format_answer(state: AgentState) -> AgentState:
    llm = get_interface_llm(temperature=0.3)

    # if retries exhausted with no results
    if not state.raw_results and state.retry_count >= 3:
        return state.model_copy(update={
            "answer": (
                "I was unable to retrieve data for your question after several attempts. "
                f"Last error:\n{state.execution_error or state.validation_error}"
            ),
        })

    data_str = json.dumps(state.raw_results, indent=2, default=str)[:4000] # token guard

    user_prompt = (
        f"Question: {state.question}\n\n"
        f"Data from the knowledge graph:\n{data_str}"
    )

    reply = llm.invoke([
        {"role": "system", "content": FORMAT_SYSTEM},
        {"role": "user",   "content": user_prompt},
    ])

    return state.model_copy(update={"answer": reply.content.strip()})