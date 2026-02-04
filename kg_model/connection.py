"""
Neo4j Database Connection Module

Handles connections to Neo4j database.
"""

from neo4j import GraphDatabase
from typing import Optional, List, Dict, Any
import os


class Neo4jConnection:
    """Manage Neo4j database connections."""
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j database URI (default: from NEO4J_URI env var or bolt://localhost:7687)
            user: Database username (default: from NEO4J_USER env var or 'neo4j')
            password: Database password (default: from NEO4J_PASSWORD env var, required)
        """
        self.uri = uri or os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = user or os.getenv('NEO4J_USER', 'neo4j')
        self.password = password or os.getenv('NEO4J_PASSWORD')
        
        if not self.password:
            raise ValueError("Password is required. Set NEO4J_PASSWORD environment variable or pass password parameter.")
        
        self.driver = None
        
    def connect(self):
        """Establish connection to Neo4j database."""
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        
    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()
            
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict]:
        """
        Execute a Cypher query and return results.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        if not self.driver:
            self.connect()
            
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def execute_write(self, query: str, parameters: Dict[str, Any] = None):
        """
        Execute a write transaction.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
        """
        if not self.driver:
            self.connect()
            
        with self.driver.session() as session:
            session.run(query, parameters or {})
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
