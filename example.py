"""
Example: Using the Supply Chain Knowledge Graph Pipeline

This script demonstrates basic usage of the pipeline components.
"""

from data_pipeline.loader import DataLoader
from data_pipeline.transformer import DataTransformer
from kg_model.connection import Neo4jConnection
from kg_model.product import get_product_suppliers_query
from kg_model.supplier import get_supplier_products_query


def example_load_and_transform():
    """Example: Load and transform data."""
    print("\n=== Loading and Transforming Data ===")
    
    # Load data
    loader = DataLoader('data')
    data = loader.load_all_data()
    print(f"Loaded {len(data)} datasets")
    
    # Transform data
    transformer = DataTransformer()
    nodes, edges = transformer.transform_all(data)
    
    # Display sample nodes
    print("\nSample Product nodes:")
    print(nodes['products'].head(3))
    
    print("\nSample SUPPLIES edges:")
    print(edges['supplies'].head(3))


def example_query_neo4j():
    """Example: Query Neo4j (requires running database)."""
    print("\n=== Querying Neo4j ===")
    print("Note: This requires a running Neo4j instance with loaded data")
    
    try:
        # Connect to Neo4j
        # Password should come from environment variable NEO4J_PASSWORD
        import os
        password = os.getenv('NEO4J_PASSWORD', 'your_password_here')
        
        conn = Neo4jConnection(
            uri='bolt://localhost:7687',
            user='neo4j',
            password=password
        )
        conn.connect()
        
        # Query: Get suppliers for a product
        query = get_product_suppliers_query()
        results = conn.execute_query(query, {'product_id': 'P001'})
        
        print(f"\nSuppliers for Product P001:")
        for result in results:
            print(f"  - {result}")
        
        conn.close()
        
    except Exception as e:
        print(f"Could not connect to Neo4j: {e}")
        print("Make sure Neo4j is running and credentials are correct")


def example_analyze_resilience():
    """Example: Analyze supply chain resilience."""
    print("\n=== Analyzing Resilience ===")
    
    loader = DataLoader('data')
    data = loader.load_all_data()
    
    # Find products with single supplier (SPOF)
    import pandas as pd
    
    # Count suppliers per product
    supplier_count = data['supplier_products'].groupby('product_id').size()
    spof_products = supplier_count[supplier_count == 1]
    
    print(f"\nProducts with single supplier (SPOF): {len(spof_products)}")
    for product_id in spof_products.index:
        product_name = data['products'][data['products']['product_id'] == product_id]['product_name'].values[0]
        print(f"  - {product_id}: {product_name}")
    
    # Find critical suppliers (serving many products)
    critical_threshold = 3
    products_per_supplier = data['supplier_products'].groupby('supplier_id').size()
    critical_suppliers = products_per_supplier[products_per_supplier >= critical_threshold]
    
    print(f"\nCritical suppliers (serving ≥{critical_threshold} products): {len(critical_suppliers)}")
    for supplier_id, count in critical_suppliers.items():
        supplier_name = data['suppliers'][data['suppliers']['supplier_id'] == supplier_id]['supplier_name'].values[0]
        print(f"  - {supplier_id}: {supplier_name} ({count} products)")


if __name__ == '__main__':
    print("="*60)
    print("Supply Chain Knowledge Graph - Usage Examples")
    print("="*60)
    
    # Run examples
    example_load_and_transform()
    example_analyze_resilience()
    example_query_neo4j()
    
    print("\n" + "="*60)
    print("For more examples, see:")
    print("  - analysis/resilience_analysis.ipynb")
    print("  - README.md")
    print("="*60)
