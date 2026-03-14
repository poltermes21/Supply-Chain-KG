"""
bloc1_operatiu.py
=================
Bloc 1 — Caracterització Operativa de la Xarxa
"Com funciona la xarxa en condicions normals?"

Consultes:
    1.1 Distribució d'enviaments (per ruta, mode, producte, origen, destí, matriu OD)
    1.2 KPIs base i taxa de retard (global + per segment)
    1.3 Distribució de delay_severity i cost_category
"""

import pandas as pd
from analysis.queries.base import run_query


class Block1Queries:

    # ── 1.1 DISTRIBUCIÓ D'ENVIAMENTS ──────────────────────────────────────────

    SHIPMENTS_BY_ROUTE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route)
        RETURN
            r.id AS route,
            count(o) AS total_shipments,
            round(100.0 * count(o) / 10000, 2) AS pct_total
        ORDER BY total_shipments DESC
    """

    SHIPMENTS_BY_TRANSPORT_MODE = """
        MATCH (o:Order)-[:USES_MODE]->(t:TransportMode)
        RETURN
            t.id AS transport_mode,
            count(o) AS total_shipments,
            round(100.0 * count(o) / 10000, 2) AS pct_total
        ORDER BY total_shipments DESC
    """

    SHIPMENTS_BY_PRODUCT_CATEGORY = """
        MATCH (o:Order)-[:TRANSPORTS]->(p:ProductCategory)
        RETURN
            p.name AS product_category,
            count(o) AS total_shipments,
            round(avg(o.order_weight_kg), 2) AS avg_weight_kg,
            round(100.0 * count(o) / 10000, 2) AS pct_total
        ORDER BY total_shipments DESC
    """

    SHIPMENTS_BY_ORIGIN_CITY = """
       MATCH (o:Order)-[:ORIGIN_FROM]->(c:City)
        RETURN
            c.id AS origin_city,
            count(o) AS total_shipments,
            round(100.0 * count(o) / 10000, 2) AS pct_total
        ORDER BY total_shipments DESC
    """

    SHIPMENTS_BY_DESTINATION_CITY = """
        MATCH (o:Order)-[:DESTINATION_TO]->(c:City)
        RETURN
            c.id AS destination_city,
            count(o) AS total_shipments,
            round(100.0 * count(o) / 10000, 2) AS pct_total
        ORDER BY total_shipments DESC
    """
    
    SHIPMENTS_OD_MATRIX = """
        MATCH (o:Order)-[:ORIGIN_FROM]->(orig:City),
        (o)-[:DESTINATION_TO]->(dest:City)
        RETURN
            orig.id AS origin,
            dest.id AS destination,
            count(o) AS total_shipments
        ORDER BY total_shipments DESC
    """
    

    # ── 1.2 KPIs BASE I TAXA DE RETARD ────────────────────────────────────────

    GLOBAL_KPIS = """
        MATCH (o:Order)
        RETURN
            count(o) AS total_orders,
            round(100.0 * sum(CASE WHEN o.is_delayed = true THEN 1 ELSE 0 END) / count(o), 2) AS delay_rate_pct,
            round(avg(o.delay_days), 2) AS avg_delay_days,
            round(avg(o.shipping_cost_usd), 2) AS avg_shipping_cost_usd,
            round(avg(o.actual_lead_time_days), 2) AS avg_actual_lead_time,
            round(avg(o.lead_time_efficiency), 4) AS avg_lead_time_efficiency,
            round(avg(o.cost_per_kg), 4) AS avg_cost_per_kg
    """

    DELAY_RATE_BY_ROUTE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route)
        RETURN
            r.id AS route,
            count(o) AS total_shipments,
            sum(CASE WHEN o.is_delayed = true THEN 1 ELSE 0 END) AS delayed_shipments,
            round(100.0 * sum(CASE WHEN o.is_delayed = true THEN 1 ELSE 0 END) / count(o)) AS delay_rate_pct,
            round(avg(o.delay_days), 2) AS avg_delay_days,
            round(avg(o.actual_lead_time_days), 2) AS avg_lead_time_days
        ORDER BY delay_rate_pct DESC
    """

    DELAY_RATE_BY_PRODUCT = """
        MATCH (o:Order)-[:TRANSPORTS]->(p:ProductCategory)
        RETURN
            p.name AS product_category,
            count(o) AS total_shipments,
            round(100.0 * sum(CASE WHEN o.is_delayed = true THEN 1 ELSE 0 END) / count(o), 2) AS delay_rate_pct,
            round(avg(o.delay_days), 2) AS avg_delay_days
        ORDER BY delay_rate_pct DESC
    """

    DELAY_RATE_BY_ORIGIN = """
        MATCH (o:Order)-[:ORIGIN_FROM]->(c:City)
        RETURN
            c.id AS origin_city,
            count(o) AS total_shipments,
            round(100.0 * sum(CASE WHEN o.is_delayed = true THEN 1 ELSE 0 END) / count(o), 2) AS delay_rate_pct,
            round(avg(o.delay_days), 2) AS avg_delay_days
        ORDER BY delay_rate_pct DESC
    """

    DELAY_RATE_BY_DESTINATION = """
        MATCH (o:Order)-[:DESTINATION_TO]->(c:City)
        RETURN
            c.id AS destination_city,
            count(o) AS total_shipments,
            round(100.0 * sum(CASE WHEN o.is_delayed = true THEN 1 ELSE 0 END) / count(o), 2) AS delay_rate_pct,
            round(avg(o.delay_days), 2) AS avg_delay_days
        ORDER BY delay_rate_pct DESC
    """

    DELAY_RATE_BY_TRANSPORT_MODE = """
        MATCH (o:Order)-[:USES_MODE]->(m:TransportMode)
        RETURN
            m.id AS transport_mode,
            count(o) AS total_shipments,
            round(100.0 * sum(CASE WHEN o.is_delayed = true THEN 1 ELSE 0 END) / count(o), 2) AS delay_rate_pct,
            round(avg(o.delay_days), 2) AS avg_delay_days,
            round(avg(o.shipping_cost_usd), 2) AS avg_cost_usd
        ORDER BY delay_rate_pct DESC
    """

    # ── 1.3 DISTRIBUCIÓ DE DELAY_SEVERITY I COST_CATEGORY ────────────────────

    DELAY_SEVERITY_GLOBAL = """
        MATCH (o:Order)
        RETURN
            o.delay_severity AS delay_severity,
            count(o) AS total,
            round(100.0 * count(o) / 10000, 2) AS pct_total
        ORDER BY
            CASE o.delay_severity
                WHEN 'None'     THEN 1
                WHEN 'Minor'    THEN 2
                WHEN 'Moderate' THEN 3
                WHEN 'Severe'   THEN 4
                WHEN 'Critical' THEN 5
            END
    """

    DELAY_SEVERITY_BY_ROUTE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route)
        RETURN
            r.id AS route,
            o.delay_severity AS delay_severity,
            count(o) AS total
        ORDER BY route,
            CASE o.delay_severity
                WHEN 'None'     THEN 1
                WHEN 'Minor'    THEN 2
                WHEN 'Moderate' THEN 3
                WHEN 'Severe'   THEN 4
                WHEN 'Critical' THEN 5
            END
    """

    COST_CATEGORY_BY_ROUTE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route)
        RETURN
            r.id AS route,
            o.cost_category AS cost_category,
            count(o) AS total,
            round(avg(o.shipping_cost_usd), 2) AS avg_cost_usd
        ORDER BY route, cost_category
    """

    COST_CATEGORY_BY_PRODUCT = """
        MATCH (o:Order)-[:TRANSPORTS]->(p:ProductCategory)
        RETURN
            p.name AS product_category,
            o.cost_category AS cost_category,
            count(o) AS total,
            round(avg(o.cost_per_kg), 4) AS avg_cost_per_kg
        ORDER BY product_category, cost_category
    """

    # ── MÈTODES D'EXECUCIÓ ────────────────────────────────────────────────────

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
    def shipments_by_origin_city(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.SHIPMENTS_BY_ORIGIN_CITY)

    @staticmethod
    def shipments_by_destination_city(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.SHIPMENTS_BY_DESTINATION_CITY)
        
    @staticmethod
    def shipments_od_matrix(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.SHIPMENTS_OD_MATRIX)

    @staticmethod
    def global_kpis(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.GLOBAL_KPIS)

    @staticmethod
    def delay_rate_by_route(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.DELAY_RATE_BY_ROUTE)

    @staticmethod
    def delay_rate_by_product(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.DELAY_RATE_BY_PRODUCT)

    @staticmethod
    def delay_rate_by_origin(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.DELAY_RATE_BY_ORIGIN)

    @staticmethod
    def delay_rate_by_destination(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.DELAY_RATE_BY_DESTINATION)

    @staticmethod
    def delay_rate_by_transport_mode(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.DELAY_RATE_BY_TRANSPORT_MODE)

    @staticmethod
    def delay_severity_global(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.DELAY_SEVERITY_GLOBAL)

    @staticmethod
    def delay_severity_by_route(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.DELAY_SEVERITY_BY_ROUTE)

    @staticmethod
    def cost_category_by_route(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.COST_CATEGORY_BY_ROUTE)

    @staticmethod
    def cost_category_by_product(driver) -> pd.DataFrame:
        return run_query(driver, Block1Queries.COST_CATEGORY_BY_PRODUCT)

    @staticmethod
    def run_all(driver) -> dict:
        """
        Executa totes les consultes del Bloc 1.
        Retorna un diccionari de DataFrames per usar a la app Streamlit.
        """
        return {
            # 1.1 Distribució
            "shipments_by_route":           Block1Queries.shipments_by_route(driver),
            "shipments_by_transport_mode":  Block1Queries.shipments_by_transport_mode(driver),
            "shipments_by_product":         Block1Queries.shipments_by_product_category(driver),
            "shipments_by_origin":          Block1Queries.shipments_by_origin_city(driver),
            "shipments_by_destination":     Block1Queries.shipments_by_destination_city(driver),
            # "shipments_od_matrix":          Block1Queries.shipments_od_matrix(driver),
            # 1.2 KPIs i retard
            "global_kpis":                  Block1Queries.global_kpis(driver),
            "delay_by_route":               Block1Queries.delay_rate_by_route(driver),
            "delay_by_product":             Block1Queries.delay_rate_by_product(driver),
            "delay_by_origin":              Block1Queries.delay_rate_by_origin(driver),
            "delay_by_destination":         Block1Queries.delay_rate_by_destination(driver),
            "delay_by_mode":                Block1Queries.delay_rate_by_transport_mode(driver),
            # 1.3 Severity i cost
            "delay_severity_global":        Block1Queries.delay_severity_global(driver),
            "delay_severity_by_route":      Block1Queries.delay_severity_by_route(driver),
            "cost_category_by_route":       Block1Queries.cost_category_by_route(driver),
            "cost_category_by_product":     Block1Queries.cost_category_by_product(driver),
        }