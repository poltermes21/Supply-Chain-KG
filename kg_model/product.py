"""
Product Entity Cypher Scripts

Cypher queries for creating and managing Product nodes.
"""

from typing import Dict, List


def create_product_query(product_data: Dict) -> str:
    """
    Generate Cypher query to create a Product node.
    
    Args:
        product_data: Dictionary containing product properties
        
    Returns:
        Cypher query string
    """
    return """
    MERGE (p:Product {product_id: $product_id})
    SET p.product_name = $product_name,
        p.category = $category,
        p.unit_price = $unit_price
    RETURN p
    """


def create_products_batch_query() -> str:
    """
    Generate Cypher query to create multiple Product nodes in batch.
    
    Returns:
        Cypher query string for batch creation
    """
    return """
    UNWIND $products AS product
    MERGE (p:Product {product_id: product.product_id})
    SET p.product_name = product.product_name,
        p.category = product.category,
        p.unit_price = product.unit_price
    """


def get_product_query() -> str:
    """Get query to retrieve a product by ID."""
    return """
    MATCH (p:Product {product_id: $product_id})
    RETURN p
    """


def get_products_by_category_query() -> str:
    """Get query to retrieve products by category."""
    return """
    MATCH (p:Product)
    WHERE p.category = $category
    RETURN p
    ORDER BY p.product_name
    """


def get_product_suppliers_query() -> str:
    """Get query to find all suppliers for a product."""
    return """
    MATCH (s:Supplier)-[r:SUPPLIES]->(p:Product {product_id: $product_id})
    RETURN s, r
    ORDER BY r.cost
    """


def get_product_risks_query() -> str:
    """Get query to find risks associated with a product."""
    return """
    MATCH (p:Product {product_id: $product_id})-[hr:HAS_RISK]->(risk:Risk)
    RETURN risk, hr.impact_level as impact_level
    ORDER BY risk.severity DESC
    """
