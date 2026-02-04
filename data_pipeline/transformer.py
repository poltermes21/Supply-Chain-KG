"""
Data Transformer Module

Transforms cleaned CSV data into nodes and edges for Neo4j ingestion.
"""

import pandas as pd
from typing import Dict, List, Tuple


class DataTransformer:
    """Transform CSV data into nodes and edges for knowledge graph."""
    
    def __init__(self):
        """Initialize the DataTransformer."""
        pass
    
    def create_product_nodes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create Product nodes from DataFrame.
        
        Expected columns: product_id, product_name, category, unit_price
        
        Args:
            df: Input DataFrame with product data
            
        Returns:
            DataFrame formatted for Product nodes
        """
        nodes = df.copy()
        
        # Ensure required columns exist
        required_cols = ['product_id', 'product_name']
        for col in required_cols:
            if col not in nodes.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Add node label
        nodes['label'] = 'Product'
        
        return nodes
    
    def create_supplier_nodes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create Supplier nodes from DataFrame.
        
        Expected columns: supplier_id, supplier_name, location, reliability_score
        
        Args:
            df: Input DataFrame with supplier data
            
        Returns:
            DataFrame formatted for Supplier nodes
        """
        nodes = df.copy()
        
        # Ensure required columns exist
        required_cols = ['supplier_id', 'supplier_name']
        for col in required_cols:
            if col not in nodes.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Add node label
        nodes['label'] = 'Supplier'
        
        return nodes
    
    def create_route_nodes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create Route nodes from DataFrame.
        
        Expected columns: route_id, origin, destination, distance, lead_time
        
        Args:
            df: Input DataFrame with route data
            
        Returns:
            DataFrame formatted for Route nodes
        """
        nodes = df.copy()
        
        # Ensure required columns exist
        required_cols = ['route_id']
        for col in required_cols:
            if col not in nodes.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Add node label
        nodes['label'] = 'Route'
        
        return nodes
    
    def create_risk_nodes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create Risk nodes from DataFrame.
        
        Expected columns: risk_id, risk_type, severity, probability
        
        Args:
            df: Input DataFrame with risk data
            
        Returns:
            DataFrame formatted for Risk nodes
        """
        nodes = df.copy()
        
        # Ensure required columns exist
        required_cols = ['risk_id', 'risk_type']
        for col in required_cols:
            if col not in nodes.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Add node label
        nodes['label'] = 'Risk'
        
        return nodes
    
    def create_supplies_edges(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create SUPPLIES relationship edges.
        
        Expected columns: supplier_id, product_id, capacity, cost
        
        Args:
            df: Input DataFrame with supplier-product relationships
            
        Returns:
            DataFrame formatted for SUPPLIES edges
        """
        edges = df.copy()
        
        # Ensure required columns exist
        required_cols = ['supplier_id', 'product_id']
        for col in required_cols:
            if col not in edges.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Add relationship type
        edges['relationship'] = 'SUPPLIES'
        edges['source_id'] = edges['supplier_id']
        edges['target_id'] = edges['product_id']
        
        return edges
    
    def create_uses_route_edges(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create USES_ROUTE relationship edges.
        
        Expected columns: supplier_id, route_id
        
        Args:
            df: Input DataFrame with supplier-route relationships
            
        Returns:
            DataFrame formatted for USES_ROUTE edges
        """
        edges = df.copy()
        
        # Ensure required columns exist
        required_cols = ['supplier_id', 'route_id']
        for col in required_cols:
            if col not in edges.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Add relationship type
        edges['relationship'] = 'USES_ROUTE'
        edges['source_id'] = edges['supplier_id']
        edges['target_id'] = edges['route_id']
        
        return edges
    
    def create_has_risk_edges(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create HAS_RISK relationship edges.
        
        Expected columns: entity_id, entity_type, risk_id, impact_level
        
        Args:
            df: Input DataFrame with entity-risk relationships
            
        Returns:
            DataFrame formatted for HAS_RISK edges
        """
        edges = df.copy()
        
        # Ensure required columns exist
        required_cols = ['entity_id', 'risk_id']
        for col in required_cols:
            if col not in edges.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Add relationship type
        edges['relationship'] = 'HAS_RISK'
        edges['source_id'] = edges['entity_id']
        edges['target_id'] = edges['risk_id']
        
        return edges
    
    def transform_all(self, data: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        """
        Transform all data into nodes and edges.
        
        Args:
            data: Dictionary of DataFrames with raw data
            
        Returns:
            Tuple of (nodes_dict, edges_dict)
        """
        nodes = {}
        edges = {}
        
        # Transform nodes
        if 'products' in data:
            nodes['products'] = self.create_product_nodes(data['products'])
        
        if 'suppliers' in data:
            nodes['suppliers'] = self.create_supplier_nodes(data['suppliers'])
        
        if 'routes' in data:
            nodes['routes'] = self.create_route_nodes(data['routes'])
        
        if 'risks' in data:
            nodes['risks'] = self.create_risk_nodes(data['risks'])
        
        # Transform edges
        if 'supplier_products' in data:
            edges['supplies'] = self.create_supplies_edges(data['supplier_products'])
        
        if 'supplier_routes' in data:
            edges['uses_route'] = self.create_uses_route_edges(data['supplier_routes'])
        
        if 'entity_risks' in data:
            edges['has_risk'] = self.create_has_risk_edges(data['entity_risks'])
        
        return nodes, edges
