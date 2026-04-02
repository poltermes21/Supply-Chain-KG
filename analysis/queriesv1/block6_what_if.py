"""
bloc6_whatif.py
===============
Block 6 — What-If Analysis and Failure Scenarios
"What happens if a critical node fails?"

Queries:
    6.1 Suez Canal blockage simulation
    6.2 Shanghai hub failure simulation
    6.3 Shortest path / alternative routes (GDS)
    6.4 Cost and lead time comparison for alternative routes
"""

import pandas as pd
from analysis.queries.base import run_query


class Bloc6Queries:

    # 6.1 SUEZ CANAL BLOCKAGE SIMULATION
    # Suez handles 34.1% of total shipments.
    # These queries quantify the impact of a full Suez blockage.

    SUEZ_IMPACT_OVERVIEW = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route {id: 'Suez'})
        RETURN
            count(o)                                            AS affected_shipments,
            round(100.0 * count(o) / 10000, 2)                 AS pct_total_network,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.actual_lead_time_days), 2)             AS avg_lead_time_days,
            round(avg(o.order_weight_kg), 2)                   AS avg_weight_kg
    """

    SUEZ_AFFECTED_OD_PAIRS = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route {id: 'Suez'}),
              (o)-[:ORIGIN_FROM]->(orig:City),
              (o)-[:DESTINATION_TO]->(dest:City)
        RETURN
            orig.id                                             AS origin,
            dest.id                                             AS destination,
            count(o)                                            AS affected_shipments,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.actual_lead_time_days), 2)             AS avg_lead_time_days
        ORDER BY affected_shipments DESC
    """

    SUEZ_AFFECTED_BY_PRODUCT = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route {id: 'Suez'}),
              (o)-[:TRANSPORTS]->(p:ProductCategory)
        RETURN
            p.name                                              AS product_category,
            count(o)                                            AS affected_shipments,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(sum(o.order_weight_kg), 2)                   AS total_weight_kg
        ORDER BY affected_shipments DESC
    """

    SUEZ_ALTERNATIVE_ROUTES = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route {id: 'Suez'}),
              (o)-[:ORIGIN_FROM]->(orig:City),
              (o)-[:DESTINATION_TO]->(dest:City)
        WITH orig, dest, count(o) AS affected_shipments
        MATCH (alt_route:Route)-[:CONNECTS]->(orig),
              (alt_route)-[:CONNECTS]->(dest)
        WHERE alt_route.id <> 'Suez'
        RETURN
            orig.id                                             AS origin,
            dest.id                                             AS destination,
            affected_shipments,
            collect(alt_route.id)                              AS alternative_routes
        ORDER BY affected_shipments DESC
    """

    SUEZ_COST_IMPACT_ESTIMATE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route {id: 'Suez'})
        WITH count(o) AS suez_shipments, avg(o.shipping_cost_usd) AS suez_avg_cost
        MATCH (alt:Order)-[:SHIPPED_VIA]->(alt_r:Route)
        WHERE alt_r.id IN ['Atlantic', 'Pacific']
        WITH suez_shipments, suez_avg_cost, avg(alt.shipping_cost_usd) AS alt_avg_cost
        RETURN
            suez_shipments                                      AS affected_shipments,
            round(suez_avg_cost, 2)                            AS current_avg_cost_usd,
            round(alt_avg_cost, 2)                             AS alternative_avg_cost_usd,
            round(alt_avg_cost - suez_avg_cost, 2)             AS estimated_cost_increase_usd,
            round(100.0 * (alt_avg_cost - suez_avg_cost) / suez_avg_cost, 2)
                                                                AS estimated_cost_increase_pct
    """

    # 6.2 SHANGHAI HUB FAILURE SIMULATION
    # Shanghai is the only bidirectional hub (origin + destination).
    # Its failure affects both outbound and inbound flows.

    SHANGHAI_FAILURE_IMPACT = """
        MATCH (o:Order)
        WHERE (o)-[:ORIGIN_FROM]->(:City {id: 'Shanghai'})
           OR (o)-[:DESTINATION_TO]->(:City {id: 'Shanghai'})
        RETURN
            count(o)                                            AS affected_shipments,
            round(100.0 * count(o) / 10000, 2)                 AS pct_total_network,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            sum(CASE WHEN o.is_disrupted = true THEN 1 ELSE 0 END)
                                                                AS already_disrupted
    """

    SHANGHAI_FAILURE_BY_ROUTE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route)
        WHERE (o)-[:ORIGIN_FROM]->(:City {id: 'Shanghai'})
           OR (o)-[:DESTINATION_TO]->(:City {id: 'Shanghai'})
        RETURN
            r.id                                                AS route,
            count(o)                                            AS affected_shipments,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.actual_lead_time_days), 2)             AS avg_lead_time_days
        ORDER BY affected_shipments DESC
    """

    SHANGHAI_FAILURE_BY_PRODUCT = """
        MATCH (o:Order)-[:TRANSPORTS]->(p:ProductCategory)
        WHERE (o)-[:ORIGIN_FROM]->(:City {id: 'Shanghai'})
           OR (o)-[:DESTINATION_TO]->(:City {id: 'Shanghai'})
        RETURN
            p.name                                              AS product_category,
            count(o)                                            AS affected_shipments,
            round(sum(o.order_weight_kg), 2)                   AS total_weight_kg,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd
        ORDER BY affected_shipments DESC
    """

    # 6.3 SHORTEST PATH / ALTERNATIVE ROUTES (GDS)
    # Given a route failure, find the shortest alternative path between cities.
    # Uses CONNECTS topology to find city-route-city paths.

    GDS_SHORTEST_PATH_DROP = """
        CALL gds.graph.drop('route_topology', false)
        YIELD graphName
    """

    GDS_SHORTEST_PATH_PROJECT = """
        CALL gds.graph.project(
            'route_topology',
            ['City', 'Route'],
            { CONNECTS: { orientation: 'UNDIRECTED' } }
        )
    """

    GDS_SHORTEST_PATH_RUN = """
        MATCH (source:City {id: $source_city}), (target:City {id: $target_city})
        CALL gds.shortestPath.dijkstra.stream('route_topology', {
            sourceNode: source,
            targetNode: target
        })
        YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
        RETURN
            [nodeId IN nodeIds | gds.util.asNode(nodeId).id]   AS path_nodes,
            totalCost                                           AS total_cost,
            length(path)                                        AS path_length
        ORDER BY totalCost ASC
        LIMIT 3
    """

    # 6.4 COST AND LEAD TIME COMPARISON FOR ALTERNATIVE ROUTES

    ROUTE_COMPARISON_BY_OD = """
        MATCH (o:Order)-[:ORIGIN_FROM]->(orig:City),
              (o)-[:DESTINATION_TO]->(dest:City),
              (o)-[:SHIPPED_VIA]->(r:Route)
        RETURN
            orig.id                                             AS origin,
            dest.id                                             AS destination,
            r.id                                                AS route,
            count(o)                                            AS total_shipments,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.actual_lead_time_days), 2)             AS avg_lead_time_days,
            round(avg(o.cost_per_kg), 4)                       AS avg_cost_per_kg,
            round(100.0 * sum(CASE WHEN o.is_delayed = true THEN 1 ELSE 0 END) / count(o), 2)
                                                                AS delay_rate_pct
        ORDER BY origin, destination, avg_cost_usd ASC
    """

    ROUTE_RESILIENCE_SCORE = """
        MATCH (r:Route)
        OPTIONAL MATCH (r)<-[:SHIPPED_VIA]-(o:Order)
        OPTIONAL MATCH (r)-[v:VULNERABLE_TO]->(d:DisruptionType)
        WITH r, d,
             count(DISTINCT o)                                  AS total_shipments,
             v.frequency                                       AS total_disruptions,
             avg(o.shipping_cost_usd)                          AS avg_cost,
             avg(o.actual_lead_time_days)                      AS avg_lead_time
        RETURN
            r.id                                                AS route,
            d.name                                              AS disruption_type
            total_shipments,
            total_disruptions,
            round(100.0 * total_disruptions / CASE WHEN total_shipments > 0 THEN total_shipments ELSE 1 END, 2)
                                                                AS disruption_rate_pct,
            round(avg_cost, 2)                                  AS avg_cost_usd,
            round(avg_lead_time, 2)                            AS avg_lead_time_days
        ORDER BY disruption_rate_pct ASC
    """

    # ── EXECUTION METHODS ─────────────────────────────────────────────────────

    @staticmethod
    def _run_gds_shortest_path(driver, source_city: str, target_city: str) -> pd.DataFrame:
        """
        Run GDS Dijkstra shortest path between two cities.
        Drops and recreates projection to ensure clean state.
        """
        with driver.session() as session:
            try:
                session.run(Bloc6Queries.GDS_SHORTEST_PATH_DROP)
            except Exception:
                pass

            session.run(Bloc6Queries.GDS_SHORTEST_PATH_PROJECT)
            result = session.run(
                Bloc6Queries.GDS_SHORTEST_PATH_RUN,
                source_city=source_city,
                target_city=target_city
            )
            df = pd.DataFrame([r.data() for r in result])

            try:
                session.run(Bloc6Queries.GDS_SHORTEST_PATH_DROP)
            except Exception:
                pass

        return df

    @staticmethod
    def suez_impact_overview(driver) -> pd.DataFrame:
        return run_query(driver, Bloc6Queries.SUEZ_IMPACT_OVERVIEW)

    @staticmethod
    def suez_affected_od_pairs(driver) -> pd.DataFrame:
        return run_query(driver, Bloc6Queries.SUEZ_AFFECTED_OD_PAIRS)

    @staticmethod
    def suez_affected_by_product(driver) -> pd.DataFrame:
        return run_query(driver, Bloc6Queries.SUEZ_AFFECTED_BY_PRODUCT)

    @staticmethod
    def suez_alternative_routes(driver) -> pd.DataFrame:
        return run_query(driver, Bloc6Queries.SUEZ_ALTERNATIVE_ROUTES)

    @staticmethod
    def suez_cost_impact_estimate(driver) -> pd.DataFrame:
        return run_query(driver, Bloc6Queries.SUEZ_COST_IMPACT_ESTIMATE)

    @staticmethod
    def shanghai_failure_impact(driver) -> pd.DataFrame:
        return run_query(driver, Bloc6Queries.SHANGHAI_FAILURE_IMPACT)

    @staticmethod
    def shanghai_failure_by_route(driver) -> pd.DataFrame:
        return run_query(driver, Bloc6Queries.SHANGHAI_FAILURE_BY_ROUTE)

    @staticmethod
    def shanghai_failure_by_product(driver) -> pd.DataFrame:
        return run_query(driver, Bloc6Queries.SHANGHAI_FAILURE_BY_PRODUCT)

    @staticmethod
    def shortest_path(driver, source_city: str, target_city: str) -> pd.DataFrame:
        """
        Find shortest alternative path between two cities.
        Example: shortest_path(driver, 'Mumbai', 'Rotterdam')
        """
        return Bloc6Queries._run_gds_shortest_path(driver, source_city, target_city)

    @staticmethod
    def route_comparison_by_od(driver) -> pd.DataFrame:
        return run_query(driver, Bloc6Queries.ROUTE_COMPARISON_BY_OD)

    @staticmethod
    def route_resilience_score(driver) -> pd.DataFrame:
        return run_query(driver, Bloc6Queries.ROUTE_RESILIENCE_SCORE)

    @staticmethod
    def run_all(driver) -> dict:
        """
        Runs all static Block 6 queries.
        Note: shortest_path requires explicit source/target parameters
        and must be called separately.
        """
        return {
            # 6.1 Suez blockage
            "suez_impact_overview":         Bloc6Queries.suez_impact_overview(driver),
            "suez_affected_od_pairs":       Bloc6Queries.suez_affected_od_pairs(driver),
            "suez_affected_by_product":     Bloc6Queries.suez_affected_by_product(driver),
            "suez_alternative_routes":      Bloc6Queries.suez_alternative_routes(driver),
            "suez_cost_impact_estimate":    Bloc6Queries.suez_cost_impact_estimate(driver),
            # 6.2 Shanghai failure
            "shanghai_failure_impact":      Bloc6Queries.shanghai_failure_impact(driver),
            "shanghai_failure_by_route":    Bloc6Queries.shanghai_failure_by_route(driver),
            "shanghai_failure_by_product":  Bloc6Queries.shanghai_failure_by_product(driver),
            # 6.4 Route comparison
            "route_comparison_by_od":       Bloc6Queries.route_comparison_by_od(driver),
            "route_resilience_score":       Bloc6Queries.route_resilience_score(driver),
        }