#!/usr/bin/env python3
"""
Supply Chain Knowledge Graph Pipeline

Main script to load data, transform it, and populate the Neo4j knowledge graph.
"""

import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_pipeline.loader import DataLoader
from data_pipeline.transformer import DataTransformer
from kg_model.connection import Neo4jConnection
from kg_model.schema import get_schema_queries
from kg_model.product import create_products_batch_query
from kg_model.supplier import create_suppliers_batch_query
from kg_model.route import create_routes_batch_query
from kg_model.risk import create_risks_batch_query
from kg_model.relationships import (
    create_supplies_batch_query,
    create_uses_route_batch_query,
    create_has_risk_batch_query
)


def setup_schema(conn):
    """Set up database schema and constraints."""
    print("\n=== Setting up database schema ===")
    schema_queries = get_schema_queries()
    
    for query in schema_queries:
        try:
            # Split multi-line queries by semicolon
            for sub_query in query.split(';'):
                sub_query = sub_query.strip()
                if sub_query:
                    conn.execute_write(sub_query)
            print(f"✓ Schema setup completed")
        except Exception as e:
            print(f"Note: {e}")


def load_and_transform_data(data_dir='data'):
    """Load and transform CSV data."""
    print("\n=== Loading and transforming data ===")
    
    loader = DataLoader(data_dir)
    transformer = DataTransformer()
    
    # Load all CSV files
    data = loader.load_all_data()
    print(f"✓ Loaded {len(data)} data files")
    
    # Transform data into nodes and edges
    nodes, edges = transformer.transform_all(data)
    print(f"✓ Transformed into {len(nodes)} node types and {len(edges)} edge types")
    
    return nodes, edges


def populate_nodes(conn, nodes):
    """Populate nodes in the knowledge graph."""
    print("\n=== Populating nodes ===")
    
    # Create Product nodes
    if 'products' in nodes:
        products = nodes['products'].to_dict('records')
        conn.execute_write(create_products_batch_query(), {'products': products})
        print(f"✓ Created {len(products)} Product nodes")
    
    # Create Supplier nodes
    if 'suppliers' in nodes:
        suppliers = nodes['suppliers'].to_dict('records')
        conn.execute_write(create_suppliers_batch_query(), {'suppliers': suppliers})
        print(f"✓ Created {len(suppliers)} Supplier nodes")
    
    # Create Route nodes
    if 'routes' in nodes:
        routes = nodes['routes'].to_dict('records')
        conn.execute_write(create_routes_batch_query(), {'routes': routes})
        print(f"✓ Created {len(routes)} Route nodes")
    
    # Create Risk nodes
    if 'risks' in nodes:
        risks = nodes['risks'].to_dict('records')
        conn.execute_write(create_risks_batch_query(), {'risks': risks})
        print(f"✓ Created {len(risks)} Risk nodes")


def populate_edges(conn, edges):
    """Populate relationships in the knowledge graph."""
    print("\n=== Populating relationships ===")
    
    # Create SUPPLIES relationships
    if 'supplies' in edges:
        supplies = edges['supplies'].to_dict('records')
        conn.execute_write(create_supplies_batch_query(), {'relationships': supplies})
        print(f"✓ Created {len(supplies)} SUPPLIES relationships")
    
    # Create USES_ROUTE relationships
    if 'uses_route' in edges:
        uses_route = edges['uses_route'].to_dict('records')
        conn.execute_write(create_uses_route_batch_query(), {'relationships': uses_route})
        print(f"✓ Created {len(uses_route)} USES_ROUTE relationships")
    
    # Create HAS_RISK relationships
    if 'has_risk' in edges:
        has_risk = edges['has_risk'].to_dict('records')
        conn.execute_write(create_has_risk_batch_query(), {'relationships': has_risk})
        print(f"✓ Created {len(has_risk)} HAS_RISK relationships")


def verify_data(conn):
    """Verify the loaded data."""
    print("\n=== Verifying data ===")
    
    # Count nodes
    count_query = """
    MATCH (p:Product) WITH count(p) as products
    MATCH (s:Supplier) WITH products, count(s) as suppliers
    MATCH (r:Route) WITH products, suppliers, count(r) as routes
    MATCH (risk:Risk) WITH products, suppliers, routes, count(risk) as risks
    RETURN products, suppliers, routes, risks
    """
    
    results = conn.execute_query(count_query)
    if results:
        counts = results[0]
        print(f"✓ Products: {counts['products']}")
        print(f"✓ Suppliers: {counts['suppliers']}")
        print(f"✓ Routes: {counts['routes']}")
        print(f"✓ Risks: {counts['risks']}")
    
    # Count relationships
    rel_query = """
    MATCH ()-[r:SUPPLIES]->() WITH count(r) as supplies
    MATCH ()-[r:USES_ROUTE]->() WITH supplies, count(r) as uses_route
    MATCH ()-[r:HAS_RISK]->() WITH supplies, uses_route, count(r) as has_risk
    RETURN supplies, uses_route, has_risk
    """
    
    rel_results = conn.execute_query(rel_query)
    if rel_results:
        rel_counts = rel_results[0]
        print(f"✓ SUPPLIES relationships: {rel_counts['supplies']}")
        print(f"✓ USES_ROUTE relationships: {rel_counts['uses_route']}")
        print(f"✓ HAS_RISK relationships: {rel_counts['has_risk']}")


def main():
    """Main pipeline execution."""
    print("="*60)
    print("Supply Chain Knowledge Graph Pipeline")
    print("="*60)
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Connect to Neo4j
        print("\n=== Connecting to Neo4j ===")
        conn = Neo4jConnection()
        conn.connect()
        print("✓ Connected to Neo4j database")
        
        # Set up schema
        setup_schema(conn)
        
        # Load and transform data
        nodes, edges = load_and_transform_data()
        
        # Populate database
        populate_nodes(conn, nodes)
        populate_edges(conn, edges)
        
        # Verify
        verify_data(conn)
        
        print("\n" + "="*60)
        print("Pipeline completed successfully!")
        print("="*60)
        print("\nNext steps:")
        print("1. Open the Jupyter notebook: jupyter notebook analysis/resilience_analysis.ipynb")
        print("2. Run the resilience analysis queries")
        print("3. Explore the knowledge graph in Neo4j Browser")
        
        # Close connection
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
