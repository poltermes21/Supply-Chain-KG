"""
block2_risk.py

Block 2 — Multidimensional Risk Analysis
"Where does risk concentrate and how strongly does it translate into disruption?"

Queries:
2.1 Global risk level distribution
2.2 Risk exposure by route
2.3 Risk exposure by product category
2.4 Risk buckets vs. operational outcomes
2.5 Joint high-risk exposure (geopolitical + weather)
2.6 Critical OD lanes by risk concentration
"""

import pandas as pd
from analysis.queries.base import run_query

class Block2Queries:
    """
    Block 2 isolates risk exposure and risk-outcome relationships.ç
    It deliberately excludes mitigation evaluation, which belongs to Block 5.
    """

    # 2.1 GLOBAL RISK LEVEL DISTRIBUTION

    RISK_LEVEL_GLOBAL = """
        MATCH (o:Order)
        WITH count(o) AS total_orders

        MATCH (o:Order)-[:HAS_RISK]->(ra:RiskAssessment)
        WITH
            total_orders,
            ra.risk_level AS risk_level,
            count(o) AS total_shipments,
            avg(ra.combined_risk_score) AS avg_combined_risk_score,
            avg(CASE WHEN o.is_disrupted THEN 1.0 ELSE 0.0 END) AS disruption_rate,
            avg(CASE WHEN o.is_delayed THEN 1.0 ELSE 0.0 END) AS delay_rate,
            avg(o.delay_days) as avg_delay_days

        RETURN
            risk_level,
            total_shipments,
            round(100.0 * total_shipments / toFloat(total_orders), 2) AS pct_total,
            round(avg_combined_risk_score, 4) AS avg_combined_risk_score,
            round(100.0 * disruption_rate, 2) AS disruption_rate_pct,
            round(100.0 * delay_rate, 2) AS delay_rate_pct,
            round(avg_delay_days, 2) as avg_delay_days
        ORDER BY
            CASE risk_level
                WHEN 'low' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'high' THEN 3
                WHEN 'critical' THEN 4
                ELSE 5
            END
    """

    # 2.2 RISK EXPOSURE BY ROUTE

    RISK_EXPOSURE_BY_ROUTE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route),
            (o)-[:HAS_RISK]->(ra:RiskAssessment)
        RETURN
            r.id AS route,
            count(o) AS total_shipments,
            round(avg(ra.combined_risk_score), 4) AS avg_combined_risk_score,
            round(avg(ra.geopolitical_risk_index), 4) AS avg_geopolitical_risk,
            round(avg(ra.weather_severity_index), 2) AS avg_weather_severity,
            round(100.0 * avg(CASE WHEN o.is_disrupted THEN 1.0 ELSE 0.0 END), 2) AS disruption_rate_pct,
            round(100.0 * avg(CASE WHEN o.is_delayed THEN 1.0 ELSE 0.0 END), 2) AS delay_rate_pct
        ORDER BY avg_combined_risk_score DESC
    """

    # 2.3 RISK EXPOSURE BY PRODUCT CATEGORY

    RISK_EXPOSURE_BY_PRODUCT = """
        MATCH (o:Order)-[:TRANSPORTS]->(p:ProductCategory),
            (o)-[:HAS_RISK]->(ra:RiskAssessment)
        RETURN
            p.name AS product_category,
            count(o) AS total_shipments,
            round(avg(ra.combined_risk_score), 4) AS avg_combined_risk_score,
            round(avg(ra.geopolitical_risk_index), 4) AS avg_geopolitical_risk,
            round(avg(ra.weather_severity_index), 2) AS avg_weather_severity,
            round(100.0 * avg(CASE WHEN o.is_disrupted THEN 1.0 ELSE 0.0 END), 2) AS disruption_rate_pct,
            round(100.0 * avg(CASE WHEN o.is_delayed THEN 1.0 ELSE 0.0 END), 2) AS delay_rate_pct
        ORDER BY avg_combined_risk_score DESC
    """
    
    # 2.4 OUTBOUND CITY RISK EXPOSURE
    OUTBOUND_CITY_RISK_EXPOSURE = """
        MATCH (o:Order)-[:ORIGIN_FROM]->(c:City),
            (o)-[:HAS_RISK]->(ra:RiskAssessment)
        RETURN
            c.id AS city,
            count(o) AS total_shipments,
            round(avg(ra.combined_risk_score), 4) AS avg_combined_risk_score,
            round(avg(ra.geopolitical_risk_index), 4) AS avg_geopolitical_risk,
            round(avg(ra.weather_severity_index), 2) AS avg_weather_severity,
            round(100.0 * avg(CASE WHEN o.is_disrupted THEN 1.0 ELSE 0.0 END), 2) AS disruption_rate_pct,
            round(100.0 * avg(CASE WHEN o.is_delayed THEN 1.0 ELSE 0.0 END), 2) AS delay_rate_pct
        ORDER BY avg_combined_risk_score DESC
    """
    
    
    # 2.5 INBOUND CITY RISK EXPOSURE
    INBOUND_CITY_RISK_EXPOSURE = """
        MATCH (o:Order)-[:DESTINATION_TO]->(c:City),
            (o)-[:HAS_RISK]->(ra:RiskAssessment)
        RETURN
            c.id AS city,
            count(o) AS total_shipments,
            round(avg(ra.combined_risk_score), 4) AS avg_combined_risk_score,
            round(avg(ra.geopolitical_risk_index), 4) AS avg_geopolitical_risk,
            round(avg(ra.weather_severity_index), 2) AS avg_weather_severity,
            round(100.0 * avg(CASE WHEN o.is_disrupted THEN 1.0 ELSE 0.0 END), 2) AS disruption_rate_pct,
            round(100.0 * avg(CASE WHEN o.is_delayed THEN 1.0 ELSE 0.0 END), 2) AS delay_rate_pct
        ORDER BY avg_combined_risk_score DESC
    """
    

    # 2.6 JOINT HIGH-RISK EXPOSURE
    JOINT_RISK_EXPOSURE = """
        MATCH (o:Order)-[:HAS_RISK]->(ra:RiskAssessment)
        WHERE ra.geopolitical_risk_index >= $geo_threshold
        AND ra.weather_severity_index >= $weather_threshold
        MATCH (o)-[:SHIPPED_VIA]->(r:Route)
        MATCH (o)-[:AFFECTED_BY]->(d:DisruptionType)

        WITH r,
            count(o) AS total_shipments,
            avg(ra.combined_risk_score) AS avg_risk,
            avg(o.delay_days) AS avg_delay,
            avg(CASE WHEN o.is_disrupted THEN 1.0 ELSE 0.0 END) AS disruption_rate,
            collect(DISTINCT coalesce(d.full_name, 'No disruption')) AS disruption_types

        RETURN
            r.id AS route,
            disruption_types,
            total_shipments,
            round(avg_risk, 4) AS avg_combined_risk_score,
            round(avg_delay, 2) AS avg_delay_days,
            round(100.0 * disruption_rate, 2) AS disruption_rate_pct
        ORDER BY total_shipments DESC
    """

    # 2.7 CRITICAL OD LANES BY RISK

    CRITICAL_LANES_BY_RISK = """
        MATCH (orig:City)-[f:CITY_FLOW]->(dest:City)
        RETURN
            orig.id AS origin,
            dest.id AS destination,
            f.shipments AS shipments,
            round(f.avg_combined_risk_score, 4) AS avg_combined_risk_score,
            round(f.disrupted_rate_pct, 2) AS disrupted_rate_pct,
            round(f.delay_rate_pct, 2) AS delay_rate_pct,
            f.primary_route AS primary_route,
            round(f.primary_route_share_pct, 2) AS primary_route_share_pct
        ORDER BY avg_combined_risk_score DESC, disrupted_rate_pct DESC, shipments DESC
    """

    # EXECUTION METHODS

    @staticmethod
    def risk_level_global(driver) -> pd.DataFrame:
        return run_query(driver, Block2Queries.RISK_LEVEL_GLOBAL)

    @staticmethod
    def risk_exposure_by_route(driver) -> pd.DataFrame:
        return run_query(driver, Block2Queries.RISK_EXPOSURE_BY_ROUTE)

    @staticmethod
    def risk_exposure_by_product(driver) -> pd.DataFrame:
        return run_query(driver, Block2Queries.RISK_EXPOSURE_BY_PRODUCT)
    
    @staticmethod
    def inbound_city_risk_exposure(driver) -> pd.DataFrame:
        return run_query(driver, Block2Queries.INBOUND_CITY_RISK_EXPOSURE)
    
    @staticmethod
    def outbound_city_risk_exposure(driver) -> pd.DataFrame:
        return run_query(driver, Block2Queries.OUTBOUND_CITY_RISK_EXPOSURE)

    @staticmethod
    def joint_risk_exposure(driver, 
                            geo_threshold: float = 0.6,
                            weather_threshold: float = 0.6) -> pd.DataFrame:
        return run_query(
            driver, 
            Block2Queries.JOINT_RISK_EXPOSURE,
            geo_threshold=geo_threshold,
            weather_threshold=weather_threshold
        )

    @staticmethod
    def critical_lanes_by_risk(driver) -> pd.DataFrame:
        return run_query(driver, Block2Queries.CRITICAL_LANES_BY_RISK)

    @staticmethod
    def run_all(driver, 
                geo_threshold: float = 0.6,
                weather_threshold: float = 0.6) -> dict:
        """
        Run all Block 2 queries.

        Returns:
            Dictionary of pandas DataFrames
        """
        return {
            "risk_level_global":            Block2Queries.risk_level_global(driver),
            "risk_exposure_by_route":       Block2Queries.risk_exposure_by_route(driver),
            "risk_exposure_by_product":     Block2Queries.risk_exposure_by_product(driver),
            "inbound_city_risk_exposure":   Block2Queries.inbound_city_risk_exposure(driver),
            "outbound_city_risk_exposure":  Block2Queries.outbound_city_risk_exposure(driver),
            "joint_risk_exposure":          Block2Queries.joint_risk_exposure(driver, 
                                                                              geo_threshold=geo_threshold,
                                                                              weather_threshold=weather_threshold),
            "critical_lanes_by_risk":       Block2Queries.critical_lanes_by_risk(driver),
        }