#!/usr/bin/env python3
"""
Test script for Supply Chain Knowledge Graph Pipeline

Validates the data pipeline, transformers, and query generation without requiring Neo4j.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_pipeline.loader import DataLoader
from data_pipeline.transformer import DataTransformer
from kg_model.product import (
    create_products_batch_query,
    get_product_suppliers_query,
    get_product_risks_query
)
from kg_model.supplier import (
    create_suppliers_batch_query,
    get_supplier_products_query,
    find_alternative_suppliers_query
)
from kg_model.route import (
    create_routes_batch_query,
    get_route_suppliers_query
)
from kg_model.risk import (
    create_risks_batch_query,
    get_high_severity_risks_query
)
from kg_model.relationships import (
    create_supplies_batch_query,
    create_uses_route_batch_query,
    create_has_risk_batch_query
)


def test_data_loading():
    """Test CSV data loading."""
    print("\n=== Testing Data Loading ===")
    
    loader = DataLoader('data')
    data = loader.load_all_data()
    
    expected_files = ['products', 'suppliers', 'routes', 'risks', 
                      'supplier_products', 'supplier_routes', 'entity_risks']
    
    for expected in expected_files:
        if expected not in data:
            print(f"✗ Missing expected file: {expected}")
            return False
        print(f"✓ Loaded {expected}: {len(data[expected])} rows")
    
    print("✓ All data files loaded successfully")
    return True


def test_data_transformation():
    """Test data transformation."""
    print("\n=== Testing Data Transformation ===")
    
    loader = DataLoader('data')
    data = loader.load_all_data()
    
    transformer = DataTransformer()
    nodes, edges = transformer.transform_all(data)
    
    # Check nodes
    expected_nodes = ['products', 'suppliers', 'routes', 'risks']
    for expected in expected_nodes:
        if expected not in nodes:
            print(f"✗ Missing node type: {expected}")
            return False
        print(f"✓ {expected} nodes: {len(nodes[expected])}")
    
    # Check edges
    expected_edges = ['supplies', 'uses_route', 'has_risk']
    for expected in expected_edges:
        if expected not in edges:
            print(f"✗ Missing edge type: {expected}")
            return False
        print(f"✓ {expected} edges: {len(edges[expected])}")
    
    print("✓ All transformations completed successfully")
    return True


def test_query_generation():
    """Test Cypher query generation."""
    print("\n=== Testing Query Generation ===")
    
    queries = {
        'Product batch creation': create_products_batch_query(),
        'Supplier batch creation': create_suppliers_batch_query(),
        'Route batch creation': create_routes_batch_query(),
        'Risk batch creation': create_risks_batch_query(),
        'SUPPLIES relationships': create_supplies_batch_query(),
        'USES_ROUTE relationships': create_uses_route_batch_query(),
        'HAS_RISK relationships': create_has_risk_batch_query(),
        'Get product suppliers': get_product_suppliers_query(),
        'Get product risks': get_product_risks_query(),
        'Get supplier products': get_supplier_products_query(),
        'Find alternative suppliers': find_alternative_suppliers_query(),
        'Get route suppliers': get_route_suppliers_query(),
        'Get high severity risks': get_high_severity_risks_query()
    }
    
    all_valid = True
    for name, query in queries.items():
        if query and isinstance(query, str) and len(query) > 10:
            print(f"✓ {name}: {len(query)} chars")
        else:
            print(f"✗ {name}: Invalid query")
            all_valid = False
    
    if all_valid:
        print("✓ All queries generated successfully")
    return all_valid


def test_data_integrity():
    """Test data integrity and relationships."""
    print("\n=== Testing Data Integrity ===")
    
    loader = DataLoader('data')
    data = loader.load_all_data()
    
    # Check referential integrity
    products = set(data['products']['product_id'])
    suppliers = set(data['suppliers']['supplier_id'])
    routes = set(data['routes']['route_id'])
    risks = set(data['risks']['risk_id'])
    
    # Check supplier_products references
    sp_suppliers = set(data['supplier_products']['supplier_id'])
    sp_products = set(data['supplier_products']['product_id'])
    
    invalid_suppliers = sp_suppliers - suppliers
    invalid_products = sp_products - products
    
    if invalid_suppliers:
        print(f"✗ Invalid supplier IDs in supplier_products: {invalid_suppliers}")
        return False
    if invalid_products:
        print(f"✗ Invalid product IDs in supplier_products: {invalid_products}")
        return False
    
    print("✓ Supplier-Product relationships are valid")
    
    # Check supplier_routes references
    sr_suppliers = set(data['supplier_routes']['supplier_id'])
    sr_routes = set(data['supplier_routes']['route_id'])
    
    invalid_suppliers = sr_suppliers - suppliers
    invalid_routes = sr_routes - routes
    
    if invalid_suppliers:
        print(f"✗ Invalid supplier IDs in supplier_routes: {invalid_suppliers}")
        return False
    if invalid_routes:
        print(f"✗ Invalid route IDs in supplier_routes: {invalid_routes}")
        return False
    
    print("✓ Supplier-Route relationships are valid")
    
    # Check entity_risks references
    er_risks = set(data['entity_risks']['risk_id'])
    invalid_risks = er_risks - risks
    
    if invalid_risks:
        print(f"✗ Invalid risk IDs in entity_risks: {invalid_risks}")
        return False
    
    print("✓ Entity-Risk relationships are valid")
    print("✓ All data integrity checks passed")
    return True


def main():
    """Run all tests."""
    print("="*60)
    print("Supply Chain Knowledge Graph Pipeline - Test Suite")
    print("="*60)
    
    tests = [
        ("Data Loading", test_data_loading),
        ("Data Transformation", test_data_transformation),
        ("Query Generation", test_query_generation),
        ("Data Integrity", test_data_integrity)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 All tests passed! Pipeline is ready to use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
