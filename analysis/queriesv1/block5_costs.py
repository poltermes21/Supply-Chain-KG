"""
bloc5_costos.py
===============
Block 5 — Cost Analysis and Mitigation Efficiency
"How much does disruption cost and which responses work?"

Queries:
    5.1 Average cost by route, product and transport mode
    5.2 cost_per_kg and cost_premium by segment
    5.3 Mitigation action effectiveness and ROI
    5.4 Air freight activation rate as system pressure indicator
"""

import pandas as pd
from analysis.queries.base import run_query


class Bloc5Queries:

    # 5.1 AVERAGE COST BY ROUTE, PRODUCT AND TRANSPORT MODE

    COST_BY_ROUTE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route)
        RETURN
            r.id                                                AS route,
            count(o)                                            AS total_shipments,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.order_weight_kg), 2)                   AS avg_weight_kg,
            round(avg(o.cost_per_kg), 4)                       AS avg_cost_per_kg,
            round(min(o.shipping_cost_usd), 2)                 AS min_cost_usd,
            round(max(o.shipping_cost_usd), 2)                 AS max_cost_usd
            
        ORDER BY avg_cost_usd DESC
    """

    COST_BY_PRODUCT = """
        MATCH (o:Order)-[:TRANSPORTS]->(p:ProductCategory)
        RETURN
            p.name                                              AS product_category,
            count(o)                                            AS total_shipments,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.order_weight_kg), 2)                   AS avg_weight_kg,
            round(avg(o.cost_per_kg), 2)                       AS avg_cost_per_kg,
            round(min(o.cost_per_kg), 2)                       AS min_cost_per_kg,
            round(max(o.cost_per_kg), 2)                       AS max_cost_per_kg
        ORDER BY avg_cost_usd DESC
    """

    COST_BY_TRANSPORT_MODE = """
        MATCH (o:Order)-[:USES_MODE]->(m:TransportMode)
        RETURN
            m.id                                                AS transport_mode,
            count(o)                                            AS total_shipments,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.cost_per_kg), 4)                       AS avg_cost_per_kg,
            round(avg(o.order_weight_kg), 2)                   AS avg_weight_kg,
            round(min(o.cost_per_kg), 4)                       AS min_cost_per_kg,
            round(max(o.cost_per_kg), 4)                       AS max_cost_per_kg
        ORDER BY avg_cost_usd DESC
    """

    COST_DISRUPTED_VS_NORMAL = """
        MATCH (o:Order)
        RETURN
            o.is_disrupted                                      AS is_disrupted,
            count(o)                                            AS total_shipments,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.cost_per_kg), 4)                       AS avg_cost_per_kg,
            round(avg(o.order_weight_kg), 2)                   AS avg_weight_kg,
            round(min(o.cost_per_kg), 4)                       AS min_cost_per_kg,
            round(max(o.cost_per_kg), 4)                       AS max_cost_per_kg
        ORDER BY is_disrupted
    """

    # 5.2 COST_PER_KG AND COST_PREMIUM BY SEGMENT

    COST_PER_KG_BY_ROUTE_AND_MODE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route),
              (o)-[:USES_MODE]->(m:TransportMode)
        RETURN
            r.id                                                AS route,
            m.id                                                AS transport_mode,
            count(o)                                            AS total_shipments,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.cost_per_kg), 4)                       AS avg_cost_per_kg,
            round(avg(o.order_weight_kg), 2)                   AS avg_weight_kg,
            round(min(o.cost_per_kg), 4)                       AS min_cost_per_kg,
            round(max(o.cost_per_kg), 4)                       AS max_cost_per_kg
        ORDER BY avg_cost_per_kg DESC
    """

    COST_PREMIUM_BY_DISRUPTION_TYPE = """
        MATCH (o:Order)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE o.is_disrupted = true
          AND d.name <> 'No_Disruption'
        RETURN
            d.name                                             AS disruption_type,
            count(o)                                            AS total_shipments,
            round(avg(o.cost_premium), 2)                      AS avg_cost_premium_pct,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.order_weight_kg), 2)                   AS avg_weight_kg,
            round(avg(o.cost_per_kg), 4)                       AS avg_cost_per_kg,
            round(min(o.cost_per_kg), 4)                       AS min_cost_per_kg,
            round(max(o.cost_per_kg), 4)                       AS max_cost_per_kg
        ORDER BY avg_cost_premium_pct DESC
    """

    COST_PREMIUM_BY_ROUTE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route)
        WHERE o.is_disrupted = true
        RETURN
            r.id                                                AS route,
            count(o)                                            AS disrupted_shipments,
            round(avg(o.cost_premium), 2)                      AS avg_cost_premium_pct,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.order_weight_kg), 2)                   AS avg_weight_kg,
            round(avg(o.cost_per_kg), 4)                       AS avg_cost_per_kg,
            round(min(o.cost_per_kg), 4)                       AS min_cost_per_kg,
            round(max(o.cost_per_kg), 4)                       AS max_cost_per_kg
        ORDER BY avg_cost_premium_pct DESC
    """

    # 5.3 MITIGATION ACTION EFFECTIVENESS AND ROI
    
    DISRUPTION_OUTCOME_BY_ACTION = """
        MATCH (o:Order)-[:MITIGATED_WITH]->(ma:MitigationAction),
              (o)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE o.is_disrupted = true
          AND d.name <> 'No_Disruption'
        RETURN
            ma.name                                             AS mitigation_action,
            count(o)                                            AS total_disrupted,
            sum(CASE WHEN o.mitigation_effectiveness = 'fully_effective'     THEN 1 ELSE 0 END) AS fully_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'partially_effective' THEN 1 ELSE 0 END) AS partially_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'not_effective'       THEN 1 ELSE 0 END) AS not_effective,
            round(100.0 * sum(CASE WHEN o.mitigation_effective = true THEN 1 ELSE 0 END) / count(o), 2)
                                                                AS effectiveness_rate_pct,
            round(avg(o.delay_days), 2)                        AS avg_delay_days,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.cost_premium), 2)                      AS avg_cost_premium_pct
        ORDER BY effectiveness_rate_pct DESC
    """

    MITIGATION_ROI_BY_ACTION = """
        MATCH (o:Order)-[:MITIGATED_WITH]->(ma:MitigationAction),
              (o)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE o.is_disrupted = true
          AND d.name <> 'No_Disruption'
          AND ma.name <> 'Standard Shipping'
        WITH ma,
             count(o)                                           AS total_disrupted,
             sum(CASE WHEN o.mitigation_effective = true THEN 1 ELSE 0 END)
                                                                AS effective_count,
             avg(o.shipping_cost_usd)                          AS avg_cost_with_mitigation,
             avg(o.delay_days)                                  AS avg_delay_with_mitigation
        MATCH (baseline:Order)-[:MITIGATED_WITH]->(std:MitigationAction {name: 'Standard Shipping'}),
              (baseline)-[:AFFECTED_BY]->(d2:DisruptionType)
        WHERE baseline.is_disrupted = false
          AND d2.name <> 'No_Disruption'
        WITH ma, total_disrupted, effective_count,
             avg_cost_with_mitigation, avg_delay_with_mitigation,
             avg(baseline.shipping_cost_usd)                   AS avg_cost_baseline,
             avg(baseline.delay_days)                          AS avg_delay_baseline
        RETURN
            ma.name                                             AS mitigation_action,
            total_disrupted,
            round(100.0 * effective_count / total_disrupted, 2) AS effectiveness_rate_pct,
            round(avg_cost_with_mitigation, 2)                 AS avg_cost_usd,
            round(avg_cost_baseline, 2)                        AS baseline_cost_usd,
            round(avg_cost_with_mitigation - avg_cost_baseline, 2)
                                                                AS cost_delta_usd,
            round(avg_delay_with_mitigation, 2)                AS avg_delay_days,
            round(avg_delay_baseline, 2)                       AS baseline_delay_days,
            round(avg_delay_baseline - avg_delay_with_mitigation, 2)
                                                                AS delay_reduction_days
        ORDER BY effectiveness_rate_pct DESC
    """

    # 5.4 AIR FREIGHT ACTIVATION RATE
    # Air freight activation as a system pressure indicator:
    # when disruptions occur, sea shipments may switch to air as emergency response.

    AIR_FREIGHT_ACTIVATION_GLOBAL = """
        MATCH (o:Order)-[:USES_MODE]->(m:TransportMode)
        RETURN
            m.id                                                AS transport_mode,
            count(o)                                            AS total_shipments,
            sum(CASE WHEN o.is_disrupted = true THEN 1 ELSE 0 END)
                                                                AS disrupted_shipments,
            round(100.0 * sum(CASE WHEN o.is_disrupted = true THEN 1 ELSE 0 END) / count(o), 2)
                                                                AS disruption_rate_pct,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd
        ORDER BY transport_mode
    """

    AIR_FREIGHT_ACTIVATION_BY_ROUTE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route),
              (o)-[:USES_MODE]->(m:TransportMode)
        WITH r,
             count(o)                                           AS total_shipments,
             sum(CASE WHEN m.id = 'Air' THEN 1 ELSE 0 END)     AS air_shipments,
             sum(CASE WHEN m.id = 'Air' AND o.is_disrupted = true THEN 1 ELSE 0 END)
                                                                AS air_disrupted
        RETURN
            r.id                                                AS route,
            total_shipments,
            air_shipments,
            round(100.0 * air_shipments / total_shipments, 2)  AS air_rate_pct,
            air_disrupted,
            round(100.0 * air_disrupted / CASE WHEN air_shipments > 0 THEN air_shipments ELSE 1 END, 2)
                                                                AS air_disruption_rate_pct
        ORDER BY air_rate_pct DESC
    """

    AIR_FREIGHT_BY_DISRUPTION_TYPE = """
        MATCH (o:Order)-[:USES_MODE]->(m:TransportMode {id: 'Air'}),
              (o)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE o.is_disrupted = true
          AND d.name <> 'no_disruption'
        RETURN
            d.name                                             AS disruption_type,
            count(o)                                            AS air_disrupted_shipments,
            round(avg(o.shipping_cost_usd), 2)                 AS avg_cost_usd,
            round(avg(o.delay_days), 2)                        AS avg_delay_days
        ORDER BY air_disrupted_shipments DESC
    """

    # ── EXECUTION METHODS ─────────────────────────────────────────────────────

    @staticmethod
    def cost_by_route(driver) -> pd.DataFrame:
        return run_query(driver, Bloc5Queries.COST_BY_ROUTE)

    @staticmethod
    def cost_by_product(driver) -> pd.DataFrame:
        return run_query(driver, Bloc5Queries.COST_BY_PRODUCT)

    @staticmethod
    def cost_by_transport_mode(driver) -> pd.DataFrame:
        return run_query(driver, Bloc5Queries.COST_BY_TRANSPORT_MODE)

    @staticmethod
    def cost_disrupted_vs_normal(driver) -> pd.DataFrame:
        return run_query(driver, Bloc5Queries.COST_DISRUPTED_VS_NORMAL)

    @staticmethod
    def cost_per_kg_by_route_and_mode(driver) -> pd.DataFrame:
        return run_query(driver, Bloc5Queries.COST_PER_KG_BY_ROUTE_AND_MODE)

    @staticmethod
    def cost_premium_by_disruption_type(driver) -> pd.DataFrame:
        return run_query(driver, Bloc5Queries.COST_PREMIUM_BY_DISRUPTION_TYPE)

    @staticmethod
    def cost_premium_by_route(driver) -> pd.DataFrame:
        return run_query(driver, Bloc5Queries.COST_PREMIUM_BY_ROUTE)

    @staticmethod
    def disruption_outcome_by_action(driver) -> pd.DataFrame:
        return run_query(driver, Bloc5Queries.DISRUPTION_OUTCOME_BY_ACTION)

    @staticmethod
    def mitigation_roi_by_action(driver) -> pd.DataFrame:
        return run_query(driver, Bloc5Queries.MITIGATION_ROI_BY_ACTION)

    @staticmethod
    def air_freight_activation_global(driver) -> pd.DataFrame:
        return run_query(driver, Bloc5Queries.AIR_FREIGHT_ACTIVATION_GLOBAL)

    @staticmethod
    def air_freight_activation_by_route(driver) -> pd.DataFrame:
        return run_query(driver, Bloc5Queries.AIR_FREIGHT_ACTIVATION_BY_ROUTE)

    @staticmethod
    def air_freight_by_disruption_type(driver) -> pd.DataFrame:
        return run_query(driver, Bloc5Queries.AIR_FREIGHT_BY_DISRUPTION_TYPE)

    @staticmethod
    def run_all(driver) -> dict:
        """
        Runs all Block 5 queries and returns a dictionary of DataFrames.
        """
        return {
            # 5.1 Cost by segment
            "cost_by_route":                    Bloc5Queries.cost_by_route(driver),
            "cost_by_product":                  Bloc5Queries.cost_by_product(driver),
            "cost_by_transport_mode":           Bloc5Queries.cost_by_transport_mode(driver),
            "cost_disrupted_vs_normal":         Bloc5Queries.cost_disrupted_vs_normal(driver),
            # 5.2 Cost per kg and cost premium
            "cost_per_kg_by_route_and_mode":    Bloc5Queries.cost_per_kg_by_route_and_mode(driver),
            "cost_premium_by_disruption":       Bloc5Queries.cost_premium_by_disruption_type(driver),
            "cost_premium_by_route":            Bloc5Queries.cost_premium_by_route(driver),
            # 5.3 Mitigation ROI
            "disruption_outcome_by_action":     Bloc5Queries.disruption_outcome_by_action(driver),
            "mitigation_roi_by_action":         Bloc5Queries.mitigation_roi_by_action(driver),
            # 5.4 Air freight activation
            "air_freight_global":               Bloc5Queries.air_freight_activation_global(driver),
            "air_freight_by_route":             Bloc5Queries.air_freight_activation_by_route(driver),
            "air_freight_by_disruption":        Bloc5Queries.air_freight_by_disruption_type(driver),
        }