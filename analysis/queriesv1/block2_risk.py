"""
Block 2 — Multidimensional Risk Analysis
"Where does risk concentrate?"

Queries:
    2.1 Risk level distribution by route and product category
    2.2 Correlation between combined_risk_score and delay_severity
    2.3 Shipments with simultaneous high risk (geopolitical + weather)
    2.4 Mitigation effectiveness grouped by risk_level
"""

import pandas as pd
from analysis.queries.base import run_query


class Bloc2Queries:

    # 2.1 RISK LEVEL DISTRIBUTION

    RISK_LEVEL_GLOBAL = """
        MATCH (o:Order)-[:HAS_RISK]->(r:RiskAssessment)
        RETURN
            r.risk_level AS risk_level,
            count(o) AS total_shipments,
            round(100.0 * count(o) / 10000, 2) AS pct_total
        ORDER BY
            CASE r.risk_level
                WHEN 'Low'      THEN 1
                WHEN 'Medium'   THEN 2
                WHEN 'High'     THEN 3
                WHEN 'Critical' THEN 4
            END
    """

    RISK_LEVEL_BY_ROUTE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(rt:Route),
              (o)-[:HAS_RISK]->(r:RiskAssessment)
        RETURN
            rt.id AS route,
            r.risk_level AS risk_level,
            count(o) AS total_shipments,
            round(100.0 * count(o) / 10000, 2) AS pct_total,
            round(avg(r.combined_risk_score), 4) AS avg_combined_risk_score
        ORDER BY route,
            CASE r.risk_level
                WHEN 'Low'      THEN 1
                WHEN 'Medium'   THEN 2
                WHEN 'High'     THEN 3
                WHEN 'Critical' THEN 4
            END
    """

    RISK_LEVEL_BY_PRODUCT = """
        MATCH (o:Order)-[:TRANSPORTS]->(p:ProductCategory),
              (o)-[:HAS_RISK]->(r:RiskAssessment)
        RETURN
            p.name AS product_category,
            r.risk_level AS risk_level,
            count(o) AS total_shipments,
            round(avg(r.combined_risk_score), 4) AS avg_combined_risk_score
        ORDER BY product_category,
            CASE r.risk_level
                WHEN 'Low'      THEN 1
                WHEN 'Medium'   THEN 2
                WHEN 'High'     THEN 3
                WHEN 'Critical' THEN 4
            END
    """

    # 2.2 CORRELATION: COMBINED_RISK_SCORE → DELAY_SEVERITY

    RISK_SCORE_VS_DELAY_SEVERITY = """
        MATCH (o:Order)-[:HAS_RISK]->(r:RiskAssessment)
        RETURN
            o.delay_severity AS delay_severity,
            round(avg(r.combined_risk_score), 4) AS avg_combined_risk_score,
            round(avg(r.geopolitical_risk_index), 4) AS avg_geopolitical_risk,
            round(avg(r.weather_severity_index), 4) AS avg_weather_severity,
            count(o) AS total_shipments
        ORDER BY
            CASE o.delay_severity
                WHEN 'None'     THEN 1
                WHEN 'Minor'    THEN 2
                WHEN 'Moderate' THEN 3
                WHEN 'Severe'   THEN 4
                WHEN 'Critical' THEN 5
            END
    """

    RISK_SCORE_VS_DELAY_DAYS = """
        MATCH (o:Order)-[:HAS_RISK]->(r:RiskAssessment)
        WHERE o.is_delayed = true
        RETURN
            r.risk_level AS risk_level,
            round(avg(o.delay_days), 2) AS avg_delay_days,
            round(avg(r.combined_risk_score), 4) AS avg_combined_risk_score,
            count(o) AS total_delayed_shipments
        ORDER BY avg_delay_days DESC
    """

    RISK_SCORE_DISTRIBUTION_BY_ROUTE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(rt:Route),
              (o)-[:HAS_RISK]->(r:RiskAssessment)
        RETURN
            rt.id AS route,
            round(avg(r.combined_risk_score), 4) AS avg_combined_risk_score,
            round(avg(r.geopolitical_risk_index), 4) AS avg_geopolitical_risk,
            round(avg(r.weather_severity_index), 4) AS avg_weather_severity,
            round(avg(r.inflation_rate_pct), 4) AS avg_inflation_rate
        ORDER BY avg_combined_risk_score DESC
    """

    # 2.3 SIMULTANEOUS HIGH RISK (GEOPOLITICAL + WEATHER)

    HIGH_RISK_BOTH_DIMENSIONS = """
        MATCH (o:Order)-[:HAS_RISK]->(r:RiskAssessment)
        WHERE r.geopolitical_risk_index > 0.6
          AND r.weather_severity_index > 0.6
        RETURN
            count(o) AS total_shipments,
            round(100.0 * count(o) / 10000, 2) AS pct_total,
            round(avg(o.delay_days), 2) AS avg_delay_days,
            round(avg(o.shipping_cost_usd), 2) AS avg_cost_usd,
            round(avg(r.combined_risk_score), 4) AS avg_combined_risk_score
    """

    HIGH_RISK_BOTH_DIMENSIONS_BY_ROUTE = """
        MATCH (o:Order)-[:SHIPPED_VIA]->(rt:Route),
              (o)-[:HAS_RISK]->(r:RiskAssessment)
        WHERE r.geopolitical_risk_index > 0.6
          AND r.weather_severity_index > 0.6
        RETURN
            rt.id AS route,
            count(o) AS total_shipments,
            round(avg(o.delay_days), 2) AS avg_delay_days,
            round(avg(r.combined_risk_score), 4) AS avg_combined_risk_score
        ORDER BY total_shipments DESC
    """

    HIGH_RISK_BOTH_DIMENSIONS_BY_DISRUPTION = """
        MATCH (o:Order)-[:HAS_RISK]->(r:RiskAssessment),
              (o)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE r.geopolitical_risk_index > 0.6
          AND r.weather_severity_index > 0.6
          AND d.name <> 'No_Disruption'
        RETURN
            d.name AS disruption_type,
            count(o) AS total_shipments,
            round(avg(o.delay_days), 2) AS avg_delay_days,
            round(avg(r.combined_risk_score), 4) AS avg_combined_risk_score
        ORDER BY total_shipments DESC
    """

    # 2.4 MITIGATION EFFECTIVENESS BY RISK LEVEL
    
    MITIGATION_EFFECTIVE_BY_RISK = """
        MATCH (o:Order)-[:HAS_RISK]->(r:RiskAssessment)
        WHERE o.is_disrupted = true
        RETURN
            r.risk_level AS risk_level,
            count(o) AS total_disrupted,
            sum(CASE WHEN o.mitigation_effectiveness = 'fully_effective'    THEN 1 ELSE 0 END) AS fully_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'partially_effective' THEN 1 ELSE 0 END) AS partially_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'not_effective'       THEN 1 ELSE 0 END) AS not_effective,
            round(100.0 * sum(CASE WHEN o.mitigation_effective = true THEN 1 ELSE 0 END) / count(o), 2) AS effectiveness_rate_pct
        ORDER BY
            CASE r.risk_level
                WHEN 'Low'      THEN 1
                WHEN 'Medium'   THEN 2
                WHEN 'High'     THEN 3
                WHEN 'Critical' THEN 4
            END
    """
    
     MITIGATION_EFFECTIVE_BY_ACTION = """
        MATCH (o:Order)-[:MITIGATED_WITH]->(ma:MitigationAction)
        WHERE o.is_disrupted = true
        RETURN
            ma.name AS mitigation_action,
            count(o) AS total_disrupted,
            sum(CASE WHEN o.mitigation_effectiveness = 'fully_effective'    THEN 1 ELSE 0 END) AS fully_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'partially_effective' THEN 1 ELSE 0 END) AS partially_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'not_effective'       THEN 1 ELSE 0 END) AS not_effective,
            round(100.0 * sum(CASE WHEN o.mitigation_effective = true THEN 1 ELSE 0 END) / count(o), 2) AS effectiveness_rate_pct,
            ORDER BY effectiveness_rate_pct DESC
    """
    
    MITIGATION_EFFECTIVENESS_BY_DISRUPTION= """
        MATCH (o:Order)-[:MITIGATED_WITH]->(ma:MitigationAction),
            (o)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE o.is_disrupted = true
        AND d.name <> 'No_Disruption'
        RETURN
            d.name AS disruption_type,
            count(o) AS total_disrupted,
            sum(CASE WHEN o.mitigation_effectiveness = 'fully_effective'     THEN 1 ELSE 0 END) AS fully_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'partially_effective' THEN 1 ELSE 0 END) AS partially_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'not_effective'       THEN 1 ELSE 0 END) AS not_effective,
            round(100.0 * sum(CASE WHEN o.mitigation_effective = true THEN 1 ELSE 0 END) / count(o), 2) AS effectiveness_rate_pct,
            round(avg(o.delay_days), 2) AS avg_delay_days
        ORDER BY disruption_type, effectiveness_rate_pct DESC
    """

    MITIGATION_EFFECTIVE_BY_RISK_AND_ACTION="""
        MATCH (o:Order)-[:HAS_RISK]->(r:RiskAssessment),
            (o)-[:MITIGATED_WITH]->(ma:MitigationAction),
            (o)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE o.is_disrupted = true
        AND d.name <> 'No_Disruption'
        RETURN
            r.risk_level AS risk_level,
            ma.name AS mitigation_action,
            count(o) AS total_disrupted,
            sum(CASE WHEN o.mitigation_effectiveness = 'fully_effective'     THEN 1 ELSE 0 END) AS fully_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'partially_effective' THEN 1 ELSE 0 END) AS partially_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'not_effective'       THEN 1 ELSE 0 END) AS not_effective,
            round(100.0 * sum(CASE WHEN o.mitigation_effective = true THEN 1 ELSE 0 END) / count(o), 2) AS effectiveness_rate_pct,
            round(avg(o.delay_days), 2) AS avg_delay_days
        ORDER BY risk_level, effectiveness_rate_pct DESC
    """
    
    MITIGATION_EFFECTIVENESS_BY_DISRUPTION_AND_ACTION = """
        MATCH (o:Order)-[:MITIGATED_WITH]->(ma:MitigationAction),
            (o)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE o.is_disrupted = true
        AND d.name <> 'No_Disruption'
        RETURN
            d.name AS disruption_type,
            ma.name AS mitigation_action,
            count(o) AS total_disrupted,
            sum(CASE WHEN o.mitigation_effectiveness = 'fully_effective'     THEN 1 ELSE 0 END) AS fully_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'partially_effective' THEN 1 ELSE 0 END) AS partially_effective,
            sum(CASE WHEN o.mitigation_effectiveness = 'not_effective'       THEN 1 ELSE 0 END) AS not_effective,
            round(100.0 * sum(CASE WHEN o.mitigation_effective = true THEN 1 ELSE 0 END) / count(o), 2) AS effectiveness_rate_pct,
            round(avg(o.delay_days), 2) AS avg_delay_days
        ORDER BY disruption_type, effectiveness_rate_pct DESC
    """
    

    # EXECUTION METHODS

    @staticmethod
    def risk_level_global(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.RISK_LEVEL_GLOBAL)

    @staticmethod
    def risk_level_by_route(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.RISK_LEVEL_BY_ROUTE)

    @staticmethod
    def risk_level_by_product(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.RISK_LEVEL_BY_PRODUCT)

    @staticmethod
    def risk_score_vs_delay_severity(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.RISK_SCORE_VS_DELAY_SEVERITY)

    @staticmethod
    def risk_score_vs_delay_days(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.RISK_SCORE_VS_DELAY_DAYS)

    @staticmethod
    def risk_score_distribution_by_route(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.RISK_SCORE_DISTRIBUTION_BY_ROUTE)

    @staticmethod
    def high_risk_both_dimensions(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.HIGH_RISK_BOTH_DIMENSIONS)

    @staticmethod
    def high_risk_both_dimensions_by_route(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.HIGH_RISK_BOTH_DIMENSIONS_BY_ROUTE)

    @staticmethod
    def high_risk_both_dimensions_by_disruption(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.HIGH_RISK_BOTH_DIMENSIONS_BY_DISRUPTION)
    
    @staticmethod
    def mitigation_effective_by_risk(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.MITIGATION_EFFECTIVE_BY_RISK)
    
    @staticmethod
    def mitigation_effective_by_action(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.MITIGATION_EFFECTIVE_BY_ACTION)
    
    @staticmethod
    def mitigation_effective_by_disruption(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.MITIGATION_EFFECTIVE_BY_DISRUPTION)

    @staticmethod
    def mitigation_effective_by_risk_and_action(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.MITIGATION_EFFECTIVE_BY_RISK_AND_ACTION)
    
    @staticmethod
    def mitigation_effective_by_disruption_and_action(driver) -> pd.DataFrame:
        return run_query(driver, Bloc2Queries.MITIGATION_EFFECTIVE_BY_DISRUPTION_AND_ACTION)
    
    

    @staticmethod
    def run_all(driver) -> dict:
        """
        Run all queries in Block2
        
        Returns:
            Dictionary of pandas DataFrames
        """
        return {
            # 2.1 Risk level distribution
            "risk_level_global":                    Bloc2Queries.risk_level_global(driver),
            "risk_level_by_route":                  Bloc2Queries.risk_level_by_route(driver),
            "risk_level_by_product":                Bloc2Queries.risk_level_by_product(driver),
            # 2.2 Risk score vs delay
            "risk_score_vs_delay_severity":         Bloc2Queries.risk_score_vs_delay_severity(driver),
            "risk_score_vs_delay_days":             Bloc2Queries.risk_score_vs_delay_days(driver),
            "risk_score_by_route":                  Bloc2Queries.risk_score_distribution_by_route(driver),
            # 2.3 Simultaneous high risk
            "high_risk_both_dimensions":            Bloc2Queries.high_risk_both_dimensions(driver),
            "high_risk_both_by_route":              Bloc2Queries.high_risk_both_dimensions_by_route(driver),
            "high_risk_both_by_disruption":         Bloc2Queries.high_risk_both_dimensions_by_disruption(driver),
            # 2.4 Mitigation effectiveness
            "mitigation_effective_by_risk":     Bloc2Queries.mitigation_effective_by_risk(driver),
            "mitigation_effective_by_action":     Bloc2Queries.mitigation_effective_by_action(driver),
            "mitigation_effective_by_disruption_type":   Bloc2Queries.mitigation_effective_by_disruption_type(driver)
            "mitigation_effective_by_risk_and_action":   Bloc2Queries.mitigation_effective_by_risk_and_action(driver)
            "mitigation_effective_by_disruption_and_action":   Bloc2Queries.mitigation_effective_by_disruption_and_action(driver)
        }