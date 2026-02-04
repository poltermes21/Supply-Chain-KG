"""
Cypher Schema Definitions

Contains schema creation and constraint definitions for the knowledge graph.
"""

# Schema creation queries
CREATE_CONSTRAINTS = """
// Create unique constraints for node IDs
CREATE CONSTRAINT product_id IF NOT EXISTS
FOR (p:Product) REQUIRE p.product_id IS UNIQUE;

CREATE CONSTRAINT supplier_id IF NOT EXISTS
FOR (s:Supplier) REQUIRE s.supplier_id IS UNIQUE;

CREATE CONSTRAINT route_id IF NOT EXISTS
FOR (r:Route) REQUIRE r.route_id IS UNIQUE;

CREATE CONSTRAINT risk_id IF NOT EXISTS
FOR (r:Risk) REQUIRE r.risk_id IS UNIQUE;
"""

# Index creation queries
CREATE_INDEXES = """
// Create indexes for frequently queried properties
CREATE INDEX product_name IF NOT EXISTS
FOR (p:Product) ON (p.product_name);

CREATE INDEX supplier_name IF NOT EXISTS
FOR (s:Supplier) ON (s.supplier_name);

CREATE INDEX risk_type IF NOT EXISTS
FOR (r:Risk) ON (r.risk_type);
"""

# Clear database query
CLEAR_DATABASE = """
MATCH (n)
DETACH DELETE n
"""


def get_schema_queries():
    """
    Get all schema setup queries.
    
    Returns:
        List of query strings for schema setup
    """
    return [
        CREATE_CONSTRAINTS,
        CREATE_INDEXES
    ]
