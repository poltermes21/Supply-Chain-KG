"""
Supplier Entity Cypher Scripts

Cypher queries for creating and managing Supplier nodes.
"""

from typing import Dict


def create_supplier_query(supplier_data: Dict) -> str:
    """
    Generate Cypher query to create a Supplier node.
    
    Args:
        supplier_data: Dictionary containing supplier properties
        
    Returns:
        Cypher query string
    """
    return """
    MERGE (s:Supplier {supplier_id: $supplier_id})
    SET s.supplier_name = $supplier_name,
        s.location = $location,
        s.reliability_score = $reliability_score
    RETURN s
    """


def create_suppliers_batch_query() -> str:
    """
    Generate Cypher query to create multiple Supplier nodes in batch.
    
    Returns:
        Cypher query string for batch creation
    """
    return """
    UNWIND $suppliers AS supplier
    MERGE (s:Supplier {supplier_id: supplier.supplier_id})
    SET s.supplier_name = supplier.supplier_name,
        s.location = supplier.location,
        s.reliability_score = supplier.reliability_score
    """


def get_supplier_query() -> str:
    """Get query to retrieve a supplier by ID."""
    return """
    MATCH (s:Supplier {supplier_id: $supplier_id})
    RETURN s
    """


def get_supplier_products_query() -> str:
    """Get query to find all products supplied by a supplier."""
    return """
    MATCH (s:Supplier {supplier_id: $supplier_id})-[r:SUPPLIES]->(p:Product)
    RETURN p, r.capacity as capacity, r.cost as cost
    ORDER BY p.product_name
    """


def get_supplier_routes_query() -> str:
    """Get query to find routes used by a supplier."""
    return """
    MATCH (s:Supplier {supplier_id: $supplier_id})-[r:USES_ROUTE]->(route:Route)
    RETURN route
    ORDER BY route.lead_time
    """


def get_supplier_risks_query() -> str:
    """Get query to find risks associated with a supplier."""
    return """
    MATCH (s:Supplier {supplier_id: $supplier_id})-[hr:HAS_RISK]->(risk:Risk)
    RETURN risk, hr.impact_level as impact_level
    ORDER BY risk.severity DESC
    """


def find_alternative_suppliers_query() -> str:
    """Get query to find alternative suppliers for a product."""
    return """
    MATCH (p:Product {product_id: $product_id})<-[:SUPPLIES]-(alt:Supplier)
    WHERE alt.supplier_id <> $current_supplier_id
    RETURN alt, alt.reliability_score as reliability
    ORDER BY alt.reliability_score DESC
    LIMIT 5
    """
