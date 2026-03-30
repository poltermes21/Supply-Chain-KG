"""
bloc4_geographic.py
===================
Block 4 — Geographic Analysis and Community Detection
"How do entities naturally cluster?"

Queries:
    4.1 Louvain Community Detection (GDS)
    4.2 Traffic concentration by country and region
    4.3 Shanghai as a bidirectional hub
    4.4 Single-country risk (dependency per country)
"""

import pandas as pd
from analysis.queries.base import run_query


class Bloc4Queries:

    # 4.1 LOUVAIN COMMUNITY DETECTION (GDS)
    # Detects natural clusters of cities and routes based on structural topology.
    # Uses CONNECTS (Route <-> City) as it defines the physical logistics network.

    GDS_LOUVAIN_DROP = """
        CALL gds.graph.drop('city_route_louvain', false)
        YIELD graphName
    """

    GDS_LOUVAIN_PROJECT = """
        CALL gds.graph.project(
            'city_route_louvain',
            ['City', 'Route'],
            { CONNECTS: { orientation: 'UNDIRECTED' } }
        )
    """

    GDS_LOUVAIN_RUN = """
        CALL gds.louvain.stream('city_route_louvain')
        YIELD nodeId, communityId
        WITH gds.util.asNode(nodeId) AS node, communityId
        RETURN
            communityId                                         AS community_id,
            labels(node)[0]                                     AS node_type,
            node.id                                             AS node_name,
            communityId                                         AS community
        ORDER BY community_id, node_type, node_name
    """

    # 4.2 TRAFFIC CONCENTRATION BY COUNTRY AND REGION

    TRAFFIC_BY_COUNTRY = """
        MATCH (o:Order)-[:ORIGIN_FROM]->(c:City)-[:LOCATED_IN]->(cn:Country)
        WITH cn, count(o) AS outbound
        MATCH (o2:Order)-[:DESTINATION_TO]->(c2:City)-[:LOCATED_IN]->(cn)
        RETURN
            cn.country_name                                     AS country,
            cn.region                                           AS region,
            count(DISTINCT o2) + outbound                       AS total_traffic,
            outbound                                            AS outbound_shipments,
            count(DISTINCT o2)                                  AS inbound_shipments
        ORDER BY total_traffic DESC
    """

    TRAFFIC_BY_REGION = """
        MATCH (o:Order)-[:ORIGIN_FROM]->(c:City)-[:LOCATED_IN]->(cn:Country)
        WITH cn.region AS region, count(o) AS outbound
        MATCH (o2:Order)-[:DESTINATION_TO]->(c2:City)-[:LOCATED_IN]->(cn2:Country)
        WHERE cn2.region = region
        RETURN
            region,
            outbound                                            AS outbound_shipments,
            count(o2)                                           AS inbound_shipments,
            outbound + count(o2)                                AS total_traffic,
            round(100.0 * (outbound + count(o2)) / 20000, 2)   AS pct_total
        ORDER BY total_traffic DESC
    """

    CITY_TRAFFIC_VOLUME = """
        MATCH (c:City)
        OPTIONAL MATCH (o1:Order)-[:ORIGIN_FROM]->(c)
        OPTIONAL MATCH (o2:Order)-[:DESTINATION_TO]->(c)
        RETURN
            c.id                                                AS city,
            count(DISTINCT o1)                                  AS outbound_shipments,
            count(DISTINCT o2)                                  AS inbound_shipments,
            count(DISTINCT o1) + count(DISTINCT o2)             AS total_traffic,
            round(100.0 * (count(DISTINCT o1) + count(DISTINCT o2)) / 20000, 2)
                                                                AS pct_total
        ORDER BY total_traffic DESC
    """

    # 4.3 SHANGHAI AS A BIDIRECTIONAL HUB
    # Shanghai is the only city appearing as both origin and destination.
    # These queries characterize its dual role and strategic importance.

    SHANGHAI_HUB_OVERVIEW = """
        MATCH (c:City {id: 'Shanghai'})
        OPTIONAL MATCH (o_out:Order)-[:ORIGIN_FROM]->(c)
        OPTIONAL MATCH (o_in:Order)-[:DESTINATION_TO]->(c)
        RETURN
            count(DISTINCT o_out)                               AS outbound_shipments,
            count(DISTINCT o_in)                                AS inbound_shipments,
            count(DISTINCT o_out) + count(DISTINCT o_in)        AS total_traffic
    """

    SHANGHAI_OUTBOUND_PROFILE = """
        MATCH (o:Order)-[:ORIGIN_FROM]->(c:City {id: 'Shanghai'}),
              (o)-[:SHIPPED_VIA]->(r:Route),
              (o)-[:DESTINATION_TO]->(dest:City)
        RETURN
            r.id                                                AS route,
            dest.id                                             AS destination,
            count(o)                                            AS shipments,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(100.0 * sum(CASE WHEN o.is_delayed = true THEN 1 ELSE 0 END) / count(o), 2)
                                                                AS delay_rate_pct
        ORDER BY shipments DESC
    """

    SHANGHAI_INBOUND_PROFILE = """
        MATCH (o:Order)-[:DESTINATION_TO]->(c:City {id: 'Shanghai'}),
              (o)-[:SHIPPED_VIA]->(r:Route),
              (o)-[:ORIGIN_FROM]->(orig:City)
        RETURN
            r.id                                                AS route,
            orig.id                                             AS origin,
            count(o)                                            AS shipments,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(100.0 * sum(CASE WHEN o.is_delayed = true THEN 1 ELSE 0 END) / count(o), 2)
                                                                AS delay_rate_pct
        ORDER BY shipments DESC
    """

    SHANGHAI_DISRUPTION_EXPOSURE = """
        MATCH (o:Order)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE (
                (o)-[:ORIGIN_FROM]->(:City {id: 'Shanghai'})
            OR (o)-[:DESTINATION_TO]->(:City {id: 'Shanghai'})
            )
        AND d.name <> 'No_Disruption'
        RETURN
            d.name AS disruption_type,
            count(o) AS disrupted_shipments,
            round(avg(o.delay_days), 2) AS avg_delay_days
        ORDER BY disrupted_shipments DESC
    """

    # 4.4 SINGLE-COUNTRY RISK
    # Measures how many shipments would be affected if a single country fails.
    # A country with high dependency = high systemic risk.

    COUNTRY_DEPENDENCY_RISK = """
        MATCH (o:Order)-[:ORIGIN_FROM]->(c:City)-[:LOCATED_IN]->(cn:Country)
        WITH cn, count(o) AS outbound_shipments
        MATCH (o2:Order)-[:DESTINATION_TO]->(c2:City)-[:LOCATED_IN]->(cn)
        WITH cn, outbound_shipments, count(o2) AS inbound_shipments
        WITH cn,
             outbound_shipments,
             inbound_shipments,
             outbound_shipments + inbound_shipments AS total_affected
        RETURN
            cn.country_name                                     AS country,
            cn.region                                           AS region,
            outbound_shipments,
            inbound_shipments,
            total_affected,
            round(100.0 * total_affected / 20000, 2)            AS pct_network_affected
        ORDER BY total_affected DESC
    """

    COUNTRY_DISRUPTION_PROFILE = """
        MATCH (o:Order)-[:ORIGIN_FROM]->(c:City)-[:LOCATED_IN]->(cn:Country),
              (o)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE d.name <> 'No_Disruption'
        RETURN
            cn.country_name                                     AS country,
            d.name                                             AS disruption_type,
            count(o)                                            AS disrupted_shipments,
            round(avg(o.delay_days), 2)                        AS avg_delay_days,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd
        ORDER BY country, disrupted_shipments DESC
    """

    # ── EXECUTION METHODS ─────────────────────────────────────────────────────

    @staticmethod
    def _run_gds_algorithm(driver, drop_query: str, project_query: str, run_query_str: str) -> pd.DataFrame:
        """Helper to safely run a GDS algorithm: drop → project → run → drop."""
        with driver.session() as session:
            try:
                session.run(drop_query)
            except Exception:
                pass

            session.run(project_query)
            result = session.run(run_query_str)
            df = pd.DataFrame([r.data() for r in result])

            try:
                session.run(drop_query)
            except Exception:
                pass

        return df

    @staticmethod
    def louvain_communities(driver) -> pd.DataFrame:
        """
        Louvain Community Detection on city-route structural graph.
        Reveals natural clusters in the logistics network topology.
        """
        return Bloc4Queries._run_gds_algorithm(
            driver,
            Bloc4Queries.GDS_LOUVAIN_DROP,
            Bloc4Queries.GDS_LOUVAIN_PROJECT,
            Bloc4Queries.GDS_LOUVAIN_RUN
        )

    @staticmethod
    def traffic_by_country(driver) -> pd.DataFrame:
        return run_query(driver, Bloc4Queries.TRAFFIC_BY_COUNTRY)

    @staticmethod
    def traffic_by_region(driver) -> pd.DataFrame:
        return run_query(driver, Bloc4Queries.TRAFFIC_BY_REGION)

    @staticmethod
    def city_traffic_volume(driver) -> pd.DataFrame:
        return run_query(driver, Bloc4Queries.CITY_TRAFFIC_VOLUME)

    @staticmethod
    def shanghai_hub_overview(driver) -> pd.DataFrame:
        return run_query(driver, Bloc4Queries.SHANGHAI_HUB_OVERVIEW)

    @staticmethod
    def shanghai_outbound_profile(driver) -> pd.DataFrame:
        return run_query(driver, Bloc4Queries.SHANGHAI_OUTBOUND_PROFILE)

    @staticmethod
    def shanghai_inbound_profile(driver) -> pd.DataFrame:
        return run_query(driver, Bloc4Queries.SHANGHAI_INBOUND_PROFILE)

    @staticmethod
    def shanghai_disruption_exposure(driver) -> pd.DataFrame:
        return run_query(driver, Bloc4Queries.SHANGHAI_DISRUPTION_EXPOSURE)

    @staticmethod
    def country_dependency_risk(driver) -> pd.DataFrame:
        return run_query(driver, Bloc4Queries.COUNTRY_DEPENDENCY_RISK)

    @staticmethod
    def country_disruption_profile(driver) -> pd.DataFrame:
        return run_query(driver, Bloc4Queries.COUNTRY_DISRUPTION_PROFILE)

    @staticmethod
    def run_all(driver) -> dict:
        """
        Runs all Block 4 queries and returns a dictionary of DataFrames.
        """
        return {
            # 4.1 Community detection
            "louvain_communities":          Bloc4Queries.louvain_communities(driver),
            # 4.2 Traffic by country and region
            "traffic_by_country":           Bloc4Queries.traffic_by_country(driver),
            "traffic_by_region":            Bloc4Queries.traffic_by_region(driver),
            "city_traffic_volume":          Bloc4Queries.city_traffic_volume(driver),
            # 4.3 Shanghai hub
            "shanghai_hub_overview":        Bloc4Queries.shanghai_hub_overview(driver),
            "shanghai_outbound_profile":    Bloc4Queries.shanghai_outbound_profile(driver),
            "shanghai_inbound_profile":     Bloc4Queries.shanghai_inbound_profile(driver),
            "shanghai_disruption_exposure": Bloc4Queries.shanghai_disruption_exposure(driver),
            # 4.4 Single-country risk
            "country_dependency_risk":      Bloc4Queries.country_dependency_risk(driver),
            "country_disruption_profile":   Bloc4Queries.country_disruption_profile(driver),
        }