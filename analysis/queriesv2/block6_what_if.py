"""
Block 6 — What-If Analysis and Failure Scenarios
"What happens if a route or a critical city fails?"

Queries:
6.1 Route-shock overview
6.2 Route-shock reroutability by OD lane
6.3 Route-shock penalty estimate from observed alternatives
6.4 Node-failure impact on directly incident lanes
6.5 Weighted shortest path on CITY_FLOW
6.6 Multi-node failure screening
"""

import pandas as pd
from typing import List, Optional
from analysis.queriesv2.base import run_query

class Block6Queries:
    """
    Block 6 is scenario-driven and therefore parameterized.
    It uses:
    - CITY_FLOW for OD-level shock analysis,
    - CITY_FLOW (directed) for weighted shortest-path exploration,
    - Order history to estimate rerouting penalties from observed alternatives.
    """

    # GDS PROJECTION: CITY_FLOW (DIRECTED)
    # Used for weighted shortest-path analysis.

    GDS_DROP_CITY_FLOW_DIRECTED = """
        CALL gds.graph.drop('city_flow_directed', false)
        YIELD graphName
    """

    GDS_PROJECT_CITY_FLOW_DIRECTED = """
        CALL gds.graph.project(
            'city_flow_directed',
            'City',
            {
                CITY_FLOW: {
                    orientation: 'NATURAL',
                    properties: [
                        'orders',
                        'avg_cost_usd',
                        'avg_lead_time_days',
                        'avg_combined_risk_score',
                        'delay_rate_pct',
                        'disruption_rate_pct'
                    ]
                }
            }
        )
    """

    # 6.1 ROUTE-SHOCK OVERVIEW

    ROUTE_SHOCK_OVERVIEW = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(:Route)
        WITH count(o) AS total_orders

        MATCH (orig:City)-[f:CITY_FLOW]->(dest:City)
        WITH
            total_orders,
            f,
            [r IN f.routes_used WHERE r IN $blocked_routes] AS blocked_hits

        WHERE size(blocked_hits) > 0

        WITH
            total_orders,
            f,
            size(blocked_hits) AS blocked_route_count,
            size(f.routes_used) AS total_routes

        WITH
            total_orders,
            sum(f.orders) AS affected_orders

        RETURN
            $blocked_routes AS blocked_routes,
            affected_orders,
            round(100.0 * affected_orders / toFloat(total_orders), 2) AS pct_total_network
    """   

    # 6.2 ROUTE-SHOCK REROUTABILITY
    # The primary route is derived from `route_share` (a JSON-encoded
    # {route_id: share} map) — it's the key with the highest value. A lane
    # is in `primary_loss` only when that dominant route is among the blocked
    # ones; otherwise (some routes blocked, primary still alive) it's a
    # `partial_loss`.

    ROUTE_SHOCK_REROUTABILITY = """
        MATCH (orig:City)-[f:CITY_FLOW]->(dest:City)
        WITH
            orig, dest, f,
            [r IN f.routes_used WHERE r IN $blocked_routes] AS blocked_hits,
            [r IN f.routes_used WHERE NOT r IN $blocked_routes] AS surviving_routes_list,
            apoc.convert.fromJsonMap(coalesce(f.route_share, '{}')) AS shares
        WHERE size(blocked_hits) > 0
        WITH
            orig, dest, f, blocked_hits, surviving_routes_list,
            reduce(maxR = ['', 0.0], r IN keys(shares) |
                CASE WHEN shares[r] > maxR[1] THEN [r, shares[r]] ELSE maxR END
            )[0] AS primary_route
        RETURN
            orig.id AS origin,
            dest.id AS destination,
            f.orders AS affected_orders,
            blocked_hits AS blocked_routes,
            surviving_routes_list AS surviving_routes,
            size(blocked_hits) AS blocked_route_count,
            size(surviving_routes_list) AS surviving_route_count,
            size(f.routes_used) AS total_routes,
            100.0 * size(blocked_hits) / size(f.routes_used) AS blocked_pct,
            primary_route,
            CASE
                WHEN size(surviving_routes_list) = 0 THEN 'fully_blocked'
                WHEN primary_route IN $blocked_routes THEN 'primary_loss'
                ELSE 'partial_loss'
            END AS shock_status
        ORDER BY surviving_route_count ASC, affected_orders DESC
    """

    # Full CITY_FLOW topology — used as a faint backdrop on the network
    # visualisations so the user can see the whole network at a glance, with
    # the affected lanes highlighted on top.
    ALL_CITY_FLOW = """
        MATCH (orig:City)-[f:CITY_FLOW]->(dest:City)
        RETURN
            orig.id AS origin,
            dest.id AS destination,
            f.orders AS orders
        ORDER BY orders DESC
    """

    # 6.3 ROUTE-SHOCK PENALTY ESTIMATE

    ROUTE_SHOCK_PENALTY_ESTIMATE = """
        MATCH (o:Order)-[:ORIGIN_FROM]->(orig:City),
            (o)-[:DESTINATION_TO]->(dest:City),
            (o)-[:SHIPPED_VIA]->(r:Route)
        WHERE r.id IN $blocked_routes
        WITH
            orig, dest, r,
            count(o) AS affected_orders,
            avg(o.shipping_cost_usd) AS base_cost,
            avg(o.actual_lead_time_days) AS base_lead
        OPTIONAL MATCH (alt:Order)-[:ORIGIN_FROM]->(orig),
                    (alt)-[:DESTINATION_TO]->(dest),
                    (alt)-[:SHIPPED_VIA]->(alt_r:Route)
        WHERE NOT alt_r.id IN $blocked_routes
        WITH
            orig, dest, r, affected_orders, base_cost, base_lead, alt_r,
            avg(alt.shipping_cost_usd) AS alt_cost,
            avg(alt.actual_lead_time_days) AS alt_lead
        RETURN
            orig.id AS origin,
            dest.id AS destination,
            r.id as blocked_route,
            affected_orders,
            CASE 
                WHEN alt_r IS NULL THEN 'no_observed_alternative'
                ELSE 'reroutable_from_history'
            END AS rerouting_feasibility,
            alt_r.id AS alternative_route,
            CASE WHEN alt_cost IS NULL THEN NULL ELSE round(alt_cost - base_cost, 2) END AS est_cost_delta_usd,
            CASE WHEN alt_lead IS NULL THEN NULL ELSE round(alt_lead - base_lead, 2) END AS est_lead_delta_days
        ORDER BY affected_orders DESC
    """

    # 6.4 NODE-FAILURE LOCAL IMPACT
    # Note:
    # This query measures the impact on lanes directly incident to the failed city.
    # It does not model hidden intermediate transit legs, since the current KG does
    # not contain explicit ShipmentLeg entities.

    NODE_FAILURE_LOCAL_IMPACT = """
        MATCH (c:City)
        WHERE c.id IN $blocked_cities

        CALL {
            WITH c
            OPTIONAL MATCH (c)-[out:CITY_FLOW]->()
            RETURN
                c.id AS city,
                coalesce(sum(out.orders), 0) AS outbound_orders,
                count(out) AS outbound_lanes
        }
        CALL {
            WITH c
            OPTIONAL MATCH ()-[inc:CITY_FLOW]->(c)
            RETURN
                coalesce(sum(inc.orders), 0) AS inbound_orders,
                count(inc) AS inbound_lanes
        }

        RETURN
            city AS blocked_city,
            outbound_orders,
            inbound_orders,
            outbound_lanes,
            inbound_lanes,
            outbound_orders + inbound_orders AS total_affected_orders
        ORDER BY total_affected_orders DESC
    """
    
    # 6.5 NODE-FAILURE GLOBAL IMPACT

    NODE_FAILURE_GLOBAL_IMPACT = """
        MATCH (orig:City)-[f:CITY_FLOW]->(dest:City)
        WHERE orig.id IN $blocked_cities
        OR dest.id IN $blocked_cities

        RETURN
            orig.id AS origin,
            dest.id AS destination,
            f.orders AS affected_orders,
            f.avg_cost_usd AS avg_cost,
            f.avg_lead_time_days AS avg_lead_time,
            f.avg_combined_risk_score AS risk_score
        ORDER BY affected_orders DESC
    """

    # 6.6 SHORTEST PATH BY WEIGHT

    SHORTEST_PATH_BY_WEIGHT = """
        MATCH (source:City {id: $source_city}),
            (target:City {id: $target_city})
        CALL gds.shortestPath.dijkstra.stream('city_flow_directed', {
            sourceNode: source,
            targetNode: target,
            relationshipWeightProperty: $weight_property
        })
        YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
        RETURN
            index,
            gds.util.asNode(sourceNode).id AS source_city,
            gds.util.asNode(targetNode).id AS target_city,
            $weight_property AS optimized_for,
            [nodeId IN nodeIds | gds.util.asNode(nodeId).id] AS path_cities,
            round(totalCost, 2) AS total_path_cost,
            [c IN costs | round(c, 2)] AS accumulated_costs
        ORDER BY index
    """

    # EXECUTION HELPERS

    @staticmethod
    def _run_query_with_params(driver, query: str, **params) -> pd.DataFrame:
        """
        Run a parameterized Cypher query and return a DataFrame.
        """
        with driver.session() as session:
            result = session.run(query, params)
            return pd.DataFrame([record.data() for record in result])

    @staticmethod
    def _run_gds_shortest_path(driver, query: str, **params) -> pd.DataFrame:
        """
        Helper to safely run a shortest-path query:
        1. Drop directed projection if exists
        2. Create directed CITY_FLOW projection
        3. Run Dijkstra
        4. Drop projection
        """
        with driver.session() as session:
            try:
                session.run(Block6Queries.GDS_DROP_CITY_FLOW_DIRECTED)
            except Exception:
                pass

            session.run(Block6Queries.GDS_PROJECT_CITY_FLOW_DIRECTED)
            result = session.run(query, params)
            df = pd.DataFrame([record.data() for record in result])

            try:
                session.run(Block6Queries.GDS_DROP_CITY_FLOW_DIRECTED)
            except Exception:
                pass

        return df

    # EXECUTION METHODS

    @staticmethod
    def route_shock_overview(driver, blocked_routes: List[str]) -> pd.DataFrame:
        return Block6Queries._run_query_with_params(
            driver,
            Block6Queries.ROUTE_SHOCK_OVERVIEW,
            blocked_routes=blocked_routes
        )

    @staticmethod
    def route_shock_reroutability(driver, blocked_routes: List[str]) -> pd.DataFrame:
        return Block6Queries._run_query_with_params(
            driver,
            Block6Queries.ROUTE_SHOCK_REROUTABILITY,
            blocked_routes=blocked_routes
        )

    @staticmethod
    def all_city_flow(driver) -> pd.DataFrame:
        """Return every CITY_FLOW edge (origin, destination, orders).

        Used as a faint backdrop on the route-shock and node-failure network
        visualisations so the user always sees the whole network, not just
        the affected slice.
        """
        return Block6Queries._run_query_with_params(
            driver,
            Block6Queries.ALL_CITY_FLOW,
        )

    @staticmethod
    def route_shock_penalty_estimate(driver, blocked_routes: List[str]) -> pd.DataFrame:
        return Block6Queries._run_query_with_params(
            driver,
            Block6Queries.ROUTE_SHOCK_PENALTY_ESTIMATE,
            blocked_routes=blocked_routes
        )

    @staticmethod
    def node_failure_local_impact(driver, blocked_cities: List[str]) -> pd.DataFrame:
        return Block6Queries._run_query_with_params(
            driver,
            Block6Queries.NODE_FAILURE_LOCAL_IMPACT,
            blocked_cities=blocked_cities
        )
        
    @staticmethod
    def node_failure_global_impact(driver, blocked_cities: List[str]) -> pd.DataFrame:
        return Block6Queries._run_query_with_params(
            driver,
            Block6Queries.NODE_FAILURE_GLOBAL_IMPACT,
            blocked_cities=blocked_cities
        )

    @staticmethod
    def shortest_path_by_weight(
        driver,
        source_city: str,
        target_city: str,
        weight_property: str = "avg_lead_time_days"
    ) -> pd.DataFrame:
        """
        Find the shortest CITY_FLOW path between two cities using a selected weight.

        Supported weights:
        - avg_lead_time_days
        - avg_cost_usd
        - avg_combined_risk_score
        """
        allowed_weights = {
            "avg_lead_time_days",
            "avg_cost_usd",
            "avg_combined_risk_score"
        }

        if weight_property not in allowed_weights:
            raise ValueError(
                f"Invalid weight_property '{weight_property}'. "
                f"Choose one of: {sorted(allowed_weights)}"
            )

        return Block6Queries._run_gds_shortest_path(
            driver,
            Block6Queries.SHORTEST_PATH_BY_WEIGHT,
            source_city=source_city,
            target_city=target_city,
            weight_property=weight_property
        )

    @staticmethod
    def run_scenario_pack(
        driver,
        blocked_routes: Optional[List[str]] = None,
        blocked_cities: Optional[List[str]] = None,
        source_city: Optional[str] = None,
        target_city: Optional[str] = None,
        weight_property: str = "avg_lead_time_days",
    ) -> dict:
        """
        Run a scenario-oriented pack of Block 6 queries.

        Args:
            blocked_routes: List of blocked routes, e.g. ['Suez']
            blocked_city:   Single failed city, e.g. 'Shanghai'
            source_city:    Source for shortest-path analysis
            target_city:    Target for shortest-path analysis
            weight_property: Weight for Dijkstra
            blocked_cities: List of failed cities for node failrues

        Returns:
            Dictionary of pandas DataFrames
        """
        results = {}

        if blocked_routes:
            results["route_shock_overview"] = Block6Queries.route_shock_overview(driver, blocked_routes)
            results["route_shock_reroutability"] = Block6Queries.route_shock_reroutability(driver, blocked_routes)
            results["route_shock_penalty_estimate"] = Block6Queries.route_shock_penalty_estimate(driver, blocked_routes)

        if blocked_cities:
            results["node_failure_local_impact"] = Block6Queries.node_failure_local_impact(driver, blocked_cities=blocked_cities)
            
        if blocked_cities:
            results["node_failure_global_impact"] = Block6Queries.node_failure_global_impact(driver,blocked_cities=blocked_cities)

        if source_city and target_city:
            results["shortest_path_by_weight"] = Block6Queries.shortest_path_by_weight(
                driver,
                source_city=source_city,
                target_city=target_city,
                weight_property=weight_property
            )

        return results