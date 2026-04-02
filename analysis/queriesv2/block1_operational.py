"""
block1_operational.py

Block 1 — Operational Baseline Characterization
"How does the supply chain perform under normal and observed conditions?"

Queries:
1.1 Global operational baseline KPIs
1.2 Shipment distribution by key business dimensions
1.3 Delay severity distribution
1.4 OD redundancy profile using CITY_FLOW
"""

import pandas as pd
from analysis.queriesv2.base import run_query

class Block1Queries:
    """
    Block 1 focuses on the operational baseline.
    The goal is to provide:
    - a dashboard-friendly baseline for Streamlit,
    - a clean operational overview before moving into risk and resilience,
    - an explicit view of OD redundancy using the new CITY_FLOW layer.
    """

    # 1.1 GLOBAL BASELINE KPIs

    GLOBAL_BASELINE_KPIS = """
        MATCH (o:Order)
        RETURN
            count(o) AS total_orders,
            round(100.0 * avg(CASE WHEN o.is_delayed THEN 1.0 ELSE 0.0 END), 2) AS delay_rate_pct,
            round(100.0 * avg(CASE WHEN o.is_disrupted THEN 1.0 ELSE 0.0 END), 2) AS disruption_rate_pct,
            round(avg(o.actual_lead_time_days), 2) AS avg_actual_lead_time_days,
            round(percentileCont(o.actual_lead_time_days, 0.95), 2) AS p95_actual_lead_time_days,
            round(avg(o.shipping_cost_usd), 2) AS avg_shipping_cost_usd,
            round(percentileCont(o.shipping_cost_usd, 0.95), 2) AS p95_shipping_cost_usd,
            round(avg(o.lead_time_efficiency), 2) AS avg_lead_time_efficiency,
            round(avg(o.cost_per_kg), 2) AS avg_cost_per_kg
    """

    # 1.2 SHIPMENT DISTRIBUTION

    SHIPMENTS_BY_ROUTE = """
        MATCH (o:Order)
        WITH count(o) AS total_orders

        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route)
        WITH r,
            total_orders,
            count(o) AS total_shipments,
            avg(o.actual_lead_time_days) AS avg_lead_time,
            avg(CASE WHEN o.is_delayed THEN 1.0 ELSE 0.0 END) AS delay_rate

        RETURN
            r.id AS route,
            total_shipments,
            round(100.0 * total_shipments / toFloat(total_orders), 2) AS pct_total,
            round(avg_lead_time, 2) AS avg_lead_time_days,
            round(100.0 * delay_rate, 2) AS delay_rate_pct
        ORDER BY total_shipments DESC
    """

    SHIPMENTS_BY_TRANSPORT_MODE = """
        MATCH (o:Order)
        WITH count(o) AS total_orders

        MATCH (o:Order)-[:USES_MODE]->(m:TransportMode)
        WITH m,
            total_orders,
            count(o) AS total_shipments,
            avg(o.actual_lead_time_days) AS avg_lead_time,
            avg(o.shipping_cost_usd) AS avg_cost,
            avg(CASE WHEN o.is_delayed THEN 1.0 ELSE 0.0 END) AS delay_rate

        RETURN
            m.id AS transport_mode,
            total_shipments,
            round(100.0 * total_shipments / toFloat(total_orders), 2) AS pct_total,
            round(avg_lead_time, 2) AS avg_lead_time_days,
            round(avg_cost, 2) AS avg_cost_usd,
            round(100.0 * delay_rate, 2) AS delay_rate_pct
        ORDER BY total_shipments DESC
    """

    SHIPMENTS_BY_PRODUCT_CATEGORY = """
        MATCH (o:Order)
        WITH count(o) AS total_orders

        MATCH (o:Order)-[:TRANSPORTS]->(p:ProductCategory)
        WITH p,
            total_orders,
            count(o) AS total_shipments,
            avg(o.order_weight_kg) AS avg_weight,
            avg(o.shipping_cost_usd) AS avg_cost,
            avg(CASE WHEN o.is_delayed THEN 1.0 ELSE 0.0 END) AS delay_rate

        RETURN
            p.name AS product_category,
            total_shipments,
            round(100.0 * total_shipments / toFloat(total_orders), 2) AS pct_total,
            round(avg_weight, 2) AS avg_weight_kg,
            round(avg_cost, 2) AS avg_cost_usd,
            round(100.0 * delay_rate, 2) AS delay_rate_pct
        ORDER BY total_shipments DESC
    """

    # 1.3 DELAY SEVERITY DISTRIBUTION

    DELAY_SEVERITY_DISTRIBUTION = """
        MATCH (o:Order)
        WITH count(o) AS total_orders

        MATCH (o:Order)
        WITH total_orders,
            o.delay_severity AS delay_severity,
            count(o) AS total_shipments

        RETURN
            delay_severity,
            total_shipments,
            round(100.0 * total_shipments / toFloat(total_orders), 2) AS pct_total
        ORDER BY
            CASE delay_severity
                WHEN 'none' THEN 1
                WHEN 'minor' THEN 2
                WHEN 'moderate' THEN 3
                WHEN 'severe' THEN 4
                WHEN 'critical' THEN 5
                ELSE 6
            END
    """

    # 1.4 OD REDUNDANCY PROFILE

    OD_REDUNDANCY_PROFILE = """
        MATCH (orig:City)-[f:CITY_FLOW]->(dest:City)
        RETURN
            orig.id AS origin,
            dest.id AS destination,
            f.shipments AS shipments,
            f.route_count AS route_count,
            f.routes_used AS routes_used,
            f.primary_route AS primary_route,
            round(f.primary_route_share_pct, 2) AS primary_route_share_pct,
            CASE
                WHEN f.route_count = 1 THEN 'single_route'
                WHEN f.primary_route_share_pct >= 80 THEN 'multi_route_but_concentrated'
                ELSE 'multi_route_diversified'
            END AS redundancy_profile,
            round(f.delay_rate_pct, 2) AS delay_rate_pct,
            round(f.avg_cost_usd, 2) AS avg_cost_usd,
            round(f.avg_lead_time_days, 2) AS avg_lead_time_days
        ORDER BY f.route_count ASC, f.primary_route_share_pct DESC, f.shipments DESC
    """

    # EXECUTION METHODS

    @staticmethod
    def global_baseline_kpis(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.GLOBAL_BASELINE_KPIS)

    @staticmethod
    def shipments_by_route(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.SHIPMENTS_BY_ROUTE)

    @staticmethod
    def shipments_by_transport_mode(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.SHIPMENTS_BY_TRANSPORT_MODE)

    @staticmethod
    def shipments_by_product_category(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.SHIPMENTS_BY_PRODUCT_CATEGORY)

    @staticmethod
    def delay_severity_distribution(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.DELAY_SEVERITY_DISTRIBUTION)

    @staticmethod
    def od_redundancy_profile(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.OD_REDUNDANCY_PROFILE)

    @staticmethod
    def run_all(driver) -> dict:
        """
        Run all Block 1 queries.

        Returns:
            Dictionary of pandas DataFrames
        """
        return {
            "global_baseline_kpis":       Block1Queries.global_baseline_kpis(driver),
            "shipments_by_route":         Block1Queries.shipments_by_route(driver),
            "shipments_by_transport_mode": Block1Queries.shipments_by_transport_mode(driver),
            "shipments_by_product":       Block1Queries.shipments_by_product_category(driver),
            "delay_severity_distribution": Block1Queries.delay_severity_distribution(driver),
            "od_redundancy_profile":      Block1Queries.od_redundancy_profile(driver),
        }