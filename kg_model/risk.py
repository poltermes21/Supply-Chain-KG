"""
Risk Entity Cypher Scripts

Cypher queries for creating and managing Risk nodes.
"""

from typing import Dict


def create_risk_query(risk_data: Dict) -> str:
    """
    Generate Cypher query to create a Risk node.
    
    Args:
        risk_data: Dictionary containing risk properties
        
    Returns:
        Cypher query string
    """
    return """
    MERGE (r:Risk {risk_id: $risk_id})
    SET r.risk_type = $risk_type,
        r.severity = $severity,
        r.probability = $probability,
        r.description = $description
    RETURN r
    """


def create_risks_batch_query() -> str:
    """
    Generate Cypher query to create multiple Risk nodes in batch.
    
    Returns:
        Cypher query string for batch creation
    """
    return """
    UNWIND $risks AS risk
    MERGE (r:Risk {risk_id: risk.risk_id})
    SET r.risk_type = risk.risk_type,
        r.severity = risk.severity,
        r.probability = risk.probability,
        r.description = risk.description
    """


def get_risk_query() -> str:
    """Get query to retrieve a risk by ID."""
    return """
    MATCH (r:Risk {risk_id: $risk_id})
    RETURN r
    """


def get_risks_by_type_query() -> str:
    """Get query to retrieve risks by type."""
    return """
    MATCH (r:Risk)
    WHERE r.risk_type = $risk_type
    RETURN r
    ORDER BY r.severity DESC, r.probability DESC
    """


def get_high_severity_risks_query() -> str:
    """Get query to find high severity risks."""
    return """
    MATCH (r:Risk)
    WHERE r.severity >= $min_severity
    RETURN r
    ORDER BY r.severity DESC, r.probability DESC
    """


def get_affected_entities_query() -> str:
    """Get query to find all entities affected by a risk."""
    return """
    MATCH (entity)-[hr:HAS_RISK]->(r:Risk {risk_id: $risk_id})
    RETURN entity, labels(entity) as entity_type, hr.impact_level as impact_level
    ORDER BY hr.impact_level DESC
    """


def create_has_risk_relationship_query() -> str:
    """Create HAS_RISK relationship between entity and risk."""
    return """
    MATCH (entity {$entity_id_property: $entity_id})
    MATCH (r:Risk {risk_id: $risk_id})
    MERGE (entity)-[hr:HAS_RISK]->(r)
    SET hr.impact_level = $impact_level
    RETURN entity, r
    """
