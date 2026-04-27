"""
block4_geographic.py

Block 4 — Geographic Analysis and Community Detection
"How does the logistics network cluster geographically and structurally?"

Queries:
4.1 Louvain community detection on CITY_FLOW
4.2 Community membership by city
4.3 Inter-community flows
4.4 Country flow exposure
4.5 Bidirectional hub profile
"""

import pandas as pd
from analysis.queriesv2.base import run_query

class Block4Queries:
    """
    Block 4 focuses on geographic clustering and territorial dependence.
    Community detection is run on the CITY_FLOW layer and written back
    to City nodes as `community_id`, which is then reused for downstream queries.
    """

    # GDS PROJECTION: CITY_FLOW (UNDIRECTED)
    # Used for community detection.

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
                        'disrupted_rate_pct'
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

        RETURN 
            city,
            outbound,
            inbound,
            total
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

    # 4.3 WRITE LOUVAIN COMMUNITY ID BACK TO CITY NODES

    LOUVAIN_WRITE_COMMUNITY_ID = """
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

    # 4.4 COMMUNITY MEMBERSHIP BY CITY

    COMMUNITIES_BY_CITY = """
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

    # EXECUTION HELPERS

    @staticmethod
    def _run_gds_write(driver, drop_query: str, project_query: str, write_query: str) -> pd.DataFrame:
        """
        Helper to safely run a GDS write algorithm:
        1. Drop projection if exists
        2. Create projection
        3. Run write algorithm
        4. Drop projection
        """
        with driver.session() as session:
            try:
                session.run(drop_query)
            except Exception:
                pass

            session.run(project_query)
            result = session.run(write_query)
            df = pd.DataFrame([record.data() for record in result])

            try:
                session.run(drop_query)
            except Exception:
                pass

        return df

    # EXECUTION METHODS
    
    @staticmethod
    def city_flow_exposure(driver) -> pd.DataFrame:
        return run_query(driver, Block4Queries.CITY_FLOW_EXPOSURE)
    
    @staticmethod
    def country_flow_exposure(driver) -> pd.DataFrame:
        return run_query(driver, Block4Queries.COUNTRY_FLOW_EXPOSURE)

    @staticmethod
    def write_community_id(driver) -> pd.DataFrame:
        """
        Run Louvain and write community_id back to City nodes.
        This method should be executed before reading community-based queries.
        """
        return Block4Queries._run_gds_write(
            driver,
            Block4Queries.GDS_DROP_CITY_FLOW_UNDIRECTED,
            Block4Queries.GDS_PROJECT_CITY_FLOW_UNDIRECTED,
            Block4Queries.LOUVAIN_WRITE_COMMUNITY_ID
        )

    @staticmethod
    def communities_by_city(driver) -> pd.DataFrame:
        return run_query(driver, Block4Queries.COMMUNITIES_BY_CITY)

    @staticmethod
    def inter_community_flows(driver) -> pd.DataFrame:
        return run_query(driver, Block4Queries.INTER_COMMUNITY_FLOWS)

    @staticmethod
    def run_all(driver) -> dict:
        """
        Run all Block 4 queries.

        Note:
            Louvain is first written back to City nodes as `community_id`,
            and the remaining queries then reuse that property.
        """
        louvain_stats = Block4Queries.write_community_id(driver)

        return {
            "city_flow_exposure": Block4Queries.city_flow_exposure(driver),
            "country_flow_exposure": Block4Queries.country_flow_exposure(driver),
            "louvain_write_stats":   louvain_stats,
            "communities_by_city":   Block4Queries.communities_by_city(driver),
            "inter_community_flows": Block4Queries.inter_community_flows(driver)
            
        }