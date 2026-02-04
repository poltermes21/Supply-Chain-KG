"""
Route Entity Cypher Scripts

Cypher queries for creating and managing Route nodes.
"""

from typing import Dict


def create_route_query(route_data: Dict) -> str:
    """
    Generate Cypher query to create a Route node.
    
    Args:
        route_data: Dictionary containing route properties
        
    Returns:
        Cypher query string
    """
    return """
    MERGE (r:Route {route_id: $route_id})
    SET r.origin = $origin,
        r.destination = $destination,
        r.distance = $distance,
        r.lead_time = $lead_time
    RETURN r
    """


def create_routes_batch_query() -> str:
    """
    Generate Cypher query to create multiple Route nodes in batch.
    
    Returns:
        Cypher query string for batch creation
    """
    return """
    UNWIND $routes AS route
    MERGE (r:Route {route_id: route.route_id})
    SET r.origin = route.origin,
        r.destination = route.destination,
        r.distance = route.distance,
        r.lead_time = route.lead_time
    """


def get_route_query() -> str:
    """Get query to retrieve a route by ID."""
    return """
    MATCH (r:Route {route_id: $route_id})
    RETURN r
    """


def get_routes_by_origin_query() -> str:
    """Get query to retrieve routes by origin."""
    return """
    MATCH (r:Route)
    WHERE r.origin = $origin
    RETURN r
    ORDER BY r.lead_time
    """


def get_routes_by_destination_query() -> str:
    """Get query to retrieve routes by destination."""
    return """
    MATCH (r:Route)
    WHERE r.destination = $destination
    RETURN r
    ORDER BY r.lead_time
    """


def get_route_suppliers_query() -> str:
    """Get query to find suppliers using a route."""
    return """
    MATCH (s:Supplier)-[:USES_ROUTE]->(r:Route {route_id: $route_id})
    RETURN s
    ORDER BY s.supplier_name
    """


def get_route_risks_query() -> str:
    """Get query to find risks associated with a route."""
    return """
    MATCH (r:Route {route_id: $route_id})-[hr:HAS_RISK]->(risk:Risk)
    RETURN risk, hr.impact_level as impact_level
    ORDER BY risk.severity DESC
    """


def find_alternative_routes_query() -> str:
    """Get query to find alternative routes between same locations."""
    return """
    MATCH (r1:Route {route_id: $route_id})
    MATCH (r2:Route)
    WHERE r2.origin = r1.origin 
      AND r2.destination = r1.destination
      AND r2.route_id <> $route_id
    RETURN r2
    ORDER BY r2.lead_time
    """
