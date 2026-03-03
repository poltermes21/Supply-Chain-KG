"""
Pytest Configuration - Shared Fixtures for Graph Tests

Provides reusable test fixtures for Neo4j connection and data access.
"""

import pytest
from neo4j import GraphDatabase
from settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


@pytest.fixture(scope="module")
def neo4j_driver():
    """
    Neo4j driver connection shared across all tests in a module.
    
    Yields:
        Neo4j driver instance
        
    Notes:
        - Scope is 'module' to reuse connection for all tests
        - Automatically closes connection after tests complete
    """
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )
    
    yield driver
    
    driver.close()


@pytest.fixture(scope="function")
def neo4j_session(neo4j_driver):
    """
    Neo4j session for executing queries.
    
    Yields:
        Neo4j session instance
        
    Notes:
        - Scope is 'function' to get a fresh session per test
        - Session automatically closes after each test
    """
    with neo4j_driver.session() as session:
        yield session