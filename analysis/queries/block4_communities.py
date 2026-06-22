"""
Block 4 — Geographic Analysis and Community Detection
"How does the logistics network cluster geographically and structurally?"
"""

import pandas as pd
from analysis.queries.base import run_query

class Block4Queries:

    # GDS PROJECTION
    GDS_DROP_CITY_FLOW_UNDIRECTED = """
        CALL gds.graph.drop('city_flow_undirected', false)
        YIELD graphName
    """

    GDS_PROJECT_CITY_FLOW_UNDIRECTED = """
        CALL gds.graph.project(
            'city_flow_undirected',
            'City',
            {
                CITY_FLOW: {
                    orientation: 'UNDIRECTED',
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

    # 4.1 CITY FLOW EXPOSURE
    
    CITY_FLOW_EXPOSURE = """
        MATCH (c:City)
        WITH 
            c.id AS city,
            c.outbound_degree AS outbound,
            c.inbound_degree as inbound,
            (c.outbound_degree + c.inbound_degree) AS total
        RETURN city, outbound, inbound, total
        ORDER BY total DESC
    """

    # 4.2 COUNTRY FLOW EXPOSURE
    
    COUNTRY_FLOW_EXPOSURE = """
        CALL {
            MATCH (:City)-[f:CITY_FLOW]->(:City)
            RETURN sum(f.orders) AS network_orders
        }
        MATCH (c:City)-[:LOCATED_IN]->(cn:Country)
        CALL {
            WITH c
            OPTIONAL MATCH (c)-[out:CITY_FLOW]->()
            RETURN sum(out.orders) AS outbound
        }
        CALL {
            WITH c
            OPTIONAL MATCH ()-[inc:CITY_FLOW]->(c)
            RETURN sum(inc.orders) AS inbound
        }
        WITH cn, network_orders,
            sum(outbound) AS outbound,
            sum(inbound) AS inbound
        RETURN
            cn.name AS country,
            cn.region AS region,
            outbound,
            inbound,
            round(100.0 * outbound / network_orders, 2) AS pct_outbound,
            round(100.0 * inbound / network_orders, 2) AS pct_inbound
        ORDER BY (outbound + inbound) DESC
    """

    # 4.3 LOUVAIN COMMUNITIES
    
    LOUVAIN_CITY_WRITE = """
        CALL gds.louvain.write('city_flow_undirected', {
            relationshipWeightProperty: 'orders',
            writeProperty: 'community_id'
        })
        YIELD communityCount, modularity, nodePropertiesWritten
        RETURN
            communityCount,
            round(modularity, 4) AS modularity_score,
            nodePropertiesWritten
    """

    # 4.4 COMMUNITY MEMBERSHIP
    
    LOUVAIN_CITY_READ = """
        MATCH (c:City)
        WHERE c.community_id IS NOT NULL
        RETURN
            c.community_id AS community_id,
            c.id AS city
        ORDER BY community_id, city
    """

    # 4.5 INTER-COMMUNITY FLOWS
    
    INTER_COMMUNITY_FLOWS = """
        MATCH (a:City)-[f:CITY_FLOW]->(b:City)
        WHERE a.community_id IS NOT NULL
        AND b.community_id IS NOT NULL
        AND a.community_id <> b.community_id
        RETURN
            a.id AS from_city,
            b.id AS to_city,
            a.community_id AS from_community,
            b.community_id AS to_community,
            f.orders AS orders,
            f.routes_used AS routes,
            round(f.avg_lead_time_days, 2) AS avg_lead_time_days
        ORDER BY orders DESC
    """
    
    # 4.6 INTRA-COMMUNITY SUMMARY
    
    INTRA_COMMUNITY_SUMMARY = """
        MATCH (a:City)-[f:CITY_FLOW]->(b:City)
        WHERE a.community_id IS NOT NULL
        AND b.community_id IS NOT NULL
        AND a.community_id = b.community_id
        RETURN
            a.community_id                              AS community_id,
            count(f)                                    AS internal_links,
            sum(f.orders)                               AS total_orders,
            round(avg(f.delay_rate_pct), 2)             AS avg_delay_rate_pct,
            round(avg(f.disruption_rate_pct), 2)        AS avg_disruption_rate_pct,
            round(avg(f.avg_cost_usd), 2)               AS avg_cost_usd,
            round(avg(f.avg_lead_time_days), 2)         AS avg_lead_time_days,
            round(avg(f.avg_combined_risk_score), 3)    AS avg_risk_score,
            round(avg(f.route_concentration), 3)        AS avg_route_concentration
    """
    
    # 4.7. INTRA-COMMUNITY OD PAIRS
    
    INTRA_COMMUNITY_OD_PAIRS = """
        MATCH (a:City)-[f:CITY_FLOW]->(b:City)
        WHERE a.community_id IS NOT NULL
        AND b.community_id IS NOT NULL
        AND a.community_id = b.community_id
        RETURN
            a.community_id                          AS community_id,
            a.id                                    AS origin,
            b.id                                    AS destination,
            f.orders                                AS orders,
            f.routes_used                           AS routes_used,
            round(f.delay_rate_pct, 2)              AS delay_rate_pct,
            round(f.disruption_rate_pct, 2)         AS disruption_rate_pct,
            round(f.route_concentration, 3)         AS route_concentration
        ORDER BY community_id, orders DESC
    """

    # EXECUTION HELPERS

    @staticmethod
    def _drop_and_project(session):
        try:
            session.run(Block4Queries.GDS_DROP_CITY_FLOW_UNDIRECTED)
        except Exception:
            pass
        session.run(Block4Queries.GDS_PROJECT_CITY_FLOW_UNDIRECTED)

    @staticmethod
    def _drop(session):
        try:
            session.run(Block4Queries.GDS_DROP_CITY_FLOW_UNDIRECTED)
        except Exception:
            pass

    # EXECUTION METHODS

    @staticmethod
    def city_flow_exposure(driver) -> pd.DataFrame:
        return run_query(driver, Block4Queries.CITY_FLOW_EXPOSURE)

    @staticmethod
    def country_flow_exposure(driver) -> pd.DataFrame:
        return run_query(driver, Block4Queries.COUNTRY_FLOW_EXPOSURE)

    @staticmethod
    def write_louvain(driver) -> pd.DataFrame:
        """Project → write community_id to City nodes → drop projection."""
        with driver.session() as session:
            Block4Queries._drop_and_project(session)
            result = session.run(Block4Queries.LOUVAIN_CITY_WRITE)
            df = pd.DataFrame([record.data() for record in result])
            Block4Queries._drop(session)
        return df

    @staticmethod
    def communities_by_city(driver) -> pd.DataFrame:
        return run_query(driver, Block4Queries.LOUVAIN_CITY_READ)

    @staticmethod
    def inter_community_flows(driver) -> pd.DataFrame:
        return run_query(driver, Block4Queries.INTER_COMMUNITY_FLOWS)
    
    @staticmethod
    def intra_community_summary(driver) -> pd.DataFrame:
        return run_query(driver, Block4Queries.INTRA_COMMUNITY_SUMMARY)
    
    @staticmethod
    def intra_community_od_pairs(driver) -> pd.DataFrame:
        return run_query(driver, Block4Queries.INTRA_COMMUNITY_OD_PAIRS)

    @staticmethod
    def write_all(driver) -> pd.DataFrame:
        """Write Louvain community_id to City nodes (call once on startup)."""
        return Block4Queries.write_louvain(driver)

    @staticmethod
    def run_all(driver) -> dict:
        """Read all Block 4 data (assumes write_all has been called)."""
        return {
            "city_flow_exposure":       Block4Queries.city_flow_exposure(driver),
            "country_flow_exposure":    Block4Queries.country_flow_exposure(driver),
            "communities_by_city":      Block4Queries.communities_by_city(driver),
            "inter_community_flows":    Block4Queries.inter_community_flows(driver),
            "intra_community_summary":  Block4Queries.intra_community_summary(driver),
            "intra_community_od_pairs": Block4Queries.intra_community_od_pairs(driver),
        }