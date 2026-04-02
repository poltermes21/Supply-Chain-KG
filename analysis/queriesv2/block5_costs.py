"""
block5_costs.py

Block 5 — Cost Analysis and Mitigation Efficiency
"How costly are disruptions and how effective are mitigation responses?"

Queries:
5.1 Disruption cost baseline
5.2 Cost of disruption by disruption type
5.3 Mitigation action summary
5.4 Mitigation performance by disruption type
5.5 Mitigation performance by disruption-route-risk context
5.6 Expedited air usage as emergency-response indicator
"""

import pandas as pd
from analysis.queriesv2.base import run_query

class Block5Queries:
    """
    Block 5 measures the economic dimension of resilience.
    The emphasis is not only on cost, but also on:
    - residual delay after mitigation,
    - recovered service level,
    - context-dependent mitigation effectiveness.
    """

    # 5.1 DISRUPTION COST BASELINE

    DISRUPTION_COST_BASELINE = """
        MATCH (o:Order)
        RETURN
            o.is_disrupted AS is_disrupted,
            count(o) AS total_shipments,
            round(avg(o.shipping_cost_usd), 2) AS avg_cost_usd,
            round(avg(o.cost_premium), 2) AS avg_cost_premium_pct,
            round(avg(o.delay_days), 2) AS avg_delay_days,
            round(100.0 * avg(CASE WHEN o.is_delayed THEN 1.0 ELSE 0.0 END), 2) AS delay_rate_pct
        ORDER BY is_disrupted DESC
    """

    # 5.2 COST OF DISRUPTION BY TYPE

    COST_OF_DISRUPTION_BY_TYPE = """
        MATCH (o:Order)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE d.name <> 'no_disruption'
        RETURN
            d.full_name AS disruption_type,
            count(o) AS total_shipments,
            round(avg(o.shipping_cost_usd), 2) AS avg_cost_usd,
            round(avg(o.cost_premium), 2) AS avg_cost_premium_pct,
            round(avg(o.delay_days), 2) AS avg_delay_days,
            round(percentileCont(o.delay_days, 0.95), 2) AS p95_delay_days
        ORDER BY avg_cost_premium_pct DESC
    """

    # 5.3 MITIGATION ACTION SUMMARY

    MITIGATION_ACTION_SUMMARY = """
        MATCH (o:Order)-[:MITIGATED_WITH]->(ma:MitigationAction),
            (o)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE d.name <> 'no_disruption'
        RETURN
            ma.name AS mitigation_action,
            count(o) AS total_cases,
            sum(CASE WHEN o.mitigation_effectiveness = 'fully_effective' THEN 1 ELSE 0 END) AS fully_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'partially_effective' THEN 1 ELSE 0 END) AS partially_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'not_effective' THEN 1 ELSE 0 END) AS not_effective,
            round(avg(o.delay_days), 2) AS residual_delay_days,
            round(avg(o.cost_premium), 2) AS avg_cost_premium_pct,
            round(100.0 * avg(CASE WHEN o.mitigation_effective THEN 1.0 ELSE 0.0 END), 2) AS effectiveness_rate_pct,
            round(
                100.0 *
                avg(CASE WHEN o.actual_lead_time_days <= o.scheduled_lead_time_days THEN 1.0 ELSE 0.0 END),
                2
            ) AS recovered_within_schedule_pct
        ORDER BY effectiveness_rate_pct DESC, residual_delay_days ASC
    """

    # 5.4 MITIGATION BY DISRUPTION TYPE

    MITIGATION_BY_DISRUPTION = """
        MATCH (o:Order)-[:MITIGATED_WITH]->(ma:MitigationAction),
            (o)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE d.name <> 'no_disruption'
        RETURN
            d.full_name AS disruption_type,
            ma.name AS mitigation_action,
            count(o) AS total_cases,
            sum(CASE WHEN o.mitigation_effectiveness = 'fully_effective' THEN 1 ELSE 0 END) AS fully_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'partially_effective' THEN 1 ELSE 0 END) AS partially_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'not_effective' THEN 1 ELSE 0 END) AS not_effective,
            round(avg(o.delay_days), 2) AS residual_delay_days,
            round(avg(o.cost_premium), 2) AS avg_cost_premium_pct,
            round(100.0 * avg(CASE WHEN o.mitigation_effective THEN 1.0 ELSE 0.0 END), 2) AS effectiveness_rate_pct,
            round(
                100.0 *
                avg(CASE WHEN o.actual_lead_time_days <= o.scheduled_lead_time_days THEN 1.0 ELSE 0.0 END),
                2
            ) AS recovered_within_schedule_pct
        ORDER BY disruption_type, effectiveness_rate_pct DESC, residual_delay_days ASC
    """

    # 5.5 MITIGATION BY CONTEXT

    MITIGATION_BY_CONTEXT = """
        MATCH (o:Order)-[:MITIGATED_WITH]->(ma:MitigationAction),
            (o)-[:AFFECTED_BY]->(d:DisruptionType),
            (o)-[:SHIPPED_VIA]->(r:Route),
            (o)-[:HAS_RISK]->(ra:RiskAssessment)
        WHERE d.name <> 'no_disruption'
        WITH
            d.full_name AS disruption_type,
            r.id AS route,
            ma.name AS mitigation_action,
            ra.risk_level AS risk_level,
            count(o) AS total_cases,
            sum(CASE WHEN o.mitigation_effectiveness = 'fully_effective' THEN 1 ELSE 0 END) AS fully_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'partially_effective' THEN 1 ELSE 0 END) AS partially_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'not_effective' THEN 1 ELSE 0 END) AS not_effective,
            avg(o.delay_days) AS residual_delay_days,
            avg(o.cost_premium) AS avg_cost_premium_pct,
            avg(CASE WHEN o.mitigation_effective THEN 1.0 ELSE 0.0 END) AS effectiveness_rate,
            avg(CASE WHEN o.actual_lead_time_days <= o.scheduled_lead_time_days THEN 1.0 ELSE 0.0 END) as recovered_within_schedule_rate
        RETURN
            disruption_type,
            route,
            risk_level,
            mitigation_action,
            total_cases,
            fully_effective,
            partially_effective,
            not_effective,
            round(residual_delay_days, 2) AS residual_delay_days,
            round(avg_cost_premium_pct, 2) AS avg_cost_premium_pct,
            round(100.0 * effectiveness_rate, 2) AS effectiveness_rate_pct,
            round(100.0 * recovered_within_schedule_rate, 2) as recovered_within_schedule_pct
        ORDER BY disruption_type, route, risk_level, effectiveness_rate_pct DESC
    """

    # 5.6 EXPEDITED AIR USAGE

    EXPEDITED_AIR_USAGE = """
        MATCH (o:Order)-[:AFFECTED_BY]->(d:DisruptionType),
            (o)-[:MITIGATED_WITH]->(ma:MitigationAction)
        WHERE d.name <> 'no_disruption'
        RETURN
            d.full_name AS disruption_type,
            count(o) AS disrupted_shipments,
            sum(CASE WHEN ma.name = 'Expedited Air Freight' THEN 1 ELSE 0 END) AS expedited_air_cases,
            round(
                100.0 * sum(CASE WHEN ma.name = 'Expedited Air Freight' THEN 1 ELSE 0 END) / toFloat(count(o)),
                2
            ) AS expedited_air_share_pct,
            round(avg(CASE WHEN ma.name = 'Expedited Air Freight' THEN o.cost_premium END), 2) AS avg_cost_premium_when_expedited
        ORDER BY expedited_air_share_pct DESC
    """

    # EXECUTION METHODS

    @staticmethod
    def disruption_cost_baseline(driver) -> pd.DataFrame:
        return run_query(driver, Block5Queries.DISRUPTION_COST_BASELINE)

    @staticmethod
    def cost_of_disruption_by_type(driver) -> pd.DataFrame:
        return run_query(driver, Block5Queries.COST_OF_DISRUPTION_BY_TYPE)

    @staticmethod
    def mitigation_action_summary(driver) -> pd.DataFrame:
        return run_query(driver, Block5Queries.MITIGATION_ACTION_SUMMARY)

    @staticmethod
    def mitigation_by_disruption(driver) -> pd.DataFrame:
        return run_query(driver, Block5Queries.MITIGATION_BY_DISRUPTION)

    @staticmethod
    def mitigation_by_context(driver) -> pd.DataFrame:
        return run_query(driver, Block5Queries.MITIGATION_BY_CONTEXT)

    @staticmethod
    def expedited_air_usage(driver) -> pd.DataFrame:
        return run_query(driver, Block5Queries.EXPEDITED_AIR_USAGE)

    @staticmethod
    def run_all(driver) -> dict:
        """
        Run all Block 5 queries.

        Returns:
            Dictionary of pandas DataFrames
        """
        return {
            "disruption_cost_baseline":   Block5Queries.disruption_cost_baseline(driver),
            "cost_of_disruption_by_type": Block5Queries.cost_of_disruption_by_type(driver),
            "mitigation_action_summary":  Block5Queries.mitigation_action_summary(driver),
            "mitigation_by_disruption":   Block5Queries.mitigation_by_disruption(driver),
            "mitigation_by_context":      Block5Queries.mitigation_by_context(driver),
            "expedited_air_usage":        Block5Queries.expedited_air_usage(driver),
        }