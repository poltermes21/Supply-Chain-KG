"""
Relationship Cypher Scripts

Cypher queries for creating and managing relationships in the knowledge graph.
"""


def create_supplies_relationship_query() -> str:
    """Create SUPPLIES relationship between Supplier and Product."""
    return """
    MATCH (s:Supplier {supplier_id: $supplier_id})
    MATCH (p:Product {product_id: $product_id})
    MERGE (s)-[r:SUPPLIES]->(p)
    SET r.capacity = $capacity,
        r.cost = $cost
    RETURN s, r, p
    """


def create_supplies_batch_query() -> str:
    """Create multiple SUPPLIES relationships in batch."""
    return """
    UNWIND $relationships AS rel
    MATCH (s:Supplier {supplier_id: rel.supplier_id})
    MATCH (p:Product {product_id: rel.product_id})
    MERGE (s)-[r:SUPPLIES]->(p)
    SET r.capacity = rel.capacity,
        r.cost = rel.cost
    """


def create_uses_route_relationship_query() -> str:
    """Create USES_ROUTE relationship between Supplier and Route."""
    return """
    MATCH (s:Supplier {supplier_id: $supplier_id})
    MATCH (r:Route {route_id: $route_id})
    MERGE (s)-[ur:USES_ROUTE]->(r)
    RETURN s, ur, r
    """


def create_uses_route_batch_query() -> str:
    """Create multiple USES_ROUTE relationships in batch."""
    return """
    UNWIND $relationships AS rel
    MATCH (s:Supplier {supplier_id: rel.supplier_id})
    MATCH (r:Route {route_id: rel.route_id})
    MERGE (s)-[ur:USES_ROUTE]->(r)
    """


def create_has_risk_batch_query() -> str:
    """Create multiple HAS_RISK relationships in batch."""
    return """
    UNWIND $relationships AS rel
    CALL {
        WITH rel
        OPTIONAL MATCH (p:Product {product_id: rel.entity_id})
        OPTIONAL MATCH (s:Supplier {supplier_id: rel.entity_id})
        OPTIONAL MATCH (ro:Route {route_id: rel.entity_id})
        WITH rel, COALESCE(p, s, ro) as entity
        WHERE entity IS NOT NULL
        MATCH (r:Risk {risk_id: rel.risk_id})
        MERGE (entity)-[hr:HAS_RISK]->(r)
        SET hr.impact_level = rel.impact_level
    }
    """
