"""
KG Extractor Module

Reads the transformed dataset and extracts all nodes and relationships
needed to build the Knowledge Graph in Neo4j.
"""

import pandas as pd
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import DATA_DIR


class KGExtractor:
    """
    Extract nodes and relationships from the transformed dataset.
    Outputs structured dictionaries ready for Neo4j ingestion.
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize the KGExtractor.

        Args:
            df: Transformed dataframe from DataTransformer
        """
        self.df = df.copy()
        self.nodes = {}
        self.relationships = {}

    # =========================================================================
    # NODE EXTRACTION
    # =========================================================================

    def extract_order_nodes(self) -> List[Dict]:
        """
        Extract Order nodes — one per row in the dataset.

        Properties extracted:
            Identification:   order_id, order_date
            Lead times:       base_lead_time_days, scheduled_lead_time_days,
                              actual_lead_time_days, delay_days
            Economic:         shipping_cost_usd, order_weight_kg
            Status:           delivery_status, cost_category
            Derived booleans: is_delayed, is_disrupted, is_mitigated, is_air_freight
            Derived metrics:  delay_severity, lead_time_efficiency,
                              cost_per_kg, delay_ratio, cost_premium

        Returns:
            List of dicts, one per Order node.
        """
        print("Extracting Order nodes...")

        order_cols = [
            'Order_ID', 'Order_Date',
            'Base_Lead_Time_Days', 'Scheduled_Lead_Time_Days',
            'Actual_Lead_Time_Days', 'Delay_Days',
            'Shipping_Cost_USD', 'Order_Weight_Kg',
            'Delivery_Status', 'cost_category',
            'is_delayed', 'is_disrupted', 'is_mitigated', 'is_air_freight',
            'delay_severity', 'lead_time_efficiency',
            'cost_per_kg', 'delay_ratio', 'cost_premium'
        ]

        nodes = []
        for _, row in self.df[order_cols].iterrows():
            order_id = row['Order_ID']
            nodes.append({
                'id':                       f"Order_{order_id}",
                'order_id':                  order_id,
                'order_date':                str(row['Order_Date'].date()) if hasattr(row['Order_Date'], 'date') else str(row['Order_Date']),
                'base_lead_time_days':       int(row['Base_Lead_Time_Days']),
                'scheduled_lead_time_days':  int(row['Scheduled_Lead_Time_Days']),
                'actual_lead_time_days':     int(row['Actual_Lead_Time_Days']),
                'delay_days':                int(row['Delay_Days']),
                'shipping_cost_usd':         round(float(row['Shipping_Cost_USD']), 2),
                'order_weight_kg':           int(row['Order_Weight_Kg']),
                'delivery_status':           row['Delivery_Status'],
                'cost_category':             row['cost_category'],
                'is_delayed':                bool(row['is_delayed']),
                'is_disrupted':              bool(row['is_disrupted']),
                'is_mitigated':              bool(row['is_mitigated']),
                'is_air_freight':            bool(row['is_air_freight']),
                'delay_severity':            row['delay_severity'],
                'lead_time_efficiency':      round(float(row['lead_time_efficiency']), 2),
                'cost_per_kg':               round(float(row['cost_per_kg']), 2),
                'delay_ratio':               round(float(row['delay_ratio']), 2),
                'cost_premium':              round(float(row['cost_premium']), 2),
            })

        self.nodes['Order'] = nodes
        print(f"   Extracted {len(nodes)} Order nodes")
        return nodes

    def extract_risk_assessment_nodes(self) -> List[Dict]:
        """
        Extract RiskAssessment nodes — one per Order (1:1 relation via HAS_RISK).

        Properties extracted:
            assessment_id, geopolitical_risk_index, weather_severity_index,
            inflation_rate_pct, combined_risk_score, risk_level,
            mitigation_effective

        Returns:
            List of dicts, one per RiskAssessment node.
        """
        print("Extracting RiskAssessment nodes...")

        risk_cols = [
            'assessment_id',
            'Geopolitical_Risk_Index', 'Weather_Severity_Index',
            'Inflation_Rate_Pct', 'combined_risk_score',
            'risk_level', 'mitigation_effective'
        ]

        nodes = []
        for _, row in self.df[risk_cols].iterrows():
            assessment_id = row['assessment_id']
            nodes.append({
                'id':                       f"Risk_{assessment_id}",
                'assessment_id':            assessment_id,
                'geopolitical_risk_index':  round(float(row['Geopolitical_Risk_Index']), 4),
                'weather_severity_index':   round(float(row['Weather_Severity_Index']), 2),
                'inflation_rate_pct':       round(float(row['Inflation_Rate_Pct']), 4),
                'combined_risk_score':      round(float(row['combined_risk_score']), 4),
                'risk_level':               row['risk_level'],
                'mitigation_effective':     bool(row['mitigation_effective']),
            })

        self.nodes['RiskAssessment'] = nodes
        print(f"   Extracted {len(nodes)} RiskAssessment nodes")
        return nodes

    def extract_route_nodes(self) -> List[Dict]:
        """
        Extract Route master nodes from unique Route_Type values.

        Properties extracted:
            route_id (= route_type), route_type

        Returns:
            List of dicts, one per unique route.
        """
        print("Extracting Route nodes...")

        nodes = []
        for route_type in self.df['Route_Type'].unique():
            nodes.append({
                'id':         f"Route_{route_type}",
                'route_id':   route_type,
                'route_type': route_type,
            })

        self.nodes['Route'] = nodes
        print(f"   Extracted {len(nodes)} Route nodes")
        return nodes

    def extract_city_nodes(self) -> List[Dict]:
        """
        Extract City master nodes from unique origin and destination city names.

        Properties extracted:
            city_name, region

        Returns:
            List of dicts, one per unique city.
        """
        print("Extracting City nodes...")

        origin_cities = self.df[['Origin_City_Name', 'Origin_Region']].rename(
            columns={'Origin_City_Name': 'city_name', 'Origin_Region': 'region'}
        )
        dest_cities = self.df[['Destination_City_Name', 'Destination_Region']].rename(
            columns={'Destination_City_Name': 'city_name', 'Destination_Region': 'region'}
        )

        all_cities = pd.concat([origin_cities, dest_cities]).drop_duplicates(subset='city_name')

        nodes = []
        for _, row in all_cities.iterrows():
            nodes.append({
                'id':        f"City_{row['city_name']}",
                'city_name': row['city_name'],
                'region':    row['region'],
            })

        self.nodes['City'] = nodes
        print(f"   Extracted {len(nodes)} City nodes")
        return nodes

    def extract_country_nodes(self) -> List[Dict]:
        """
        Extract Country master nodes from unique origin and destination countries.

        Properties extracted:
            country_name, country_code, region

        Returns:
            List of dicts, one per unique country.
        """
        print("Extracting Country nodes...")

        origin_countries = self.df[['Origin_Country', 'Origin_Country_Code', 'Origin_Region']].rename(
            columns={
                'Origin_Country':      'country_name',
                'Origin_Country_Code': 'country_code',
                'Origin_Region':       'region'
            }
        )
        dest_countries = self.df[['Destination_Country', 'Destination_Country_Code', 'Destination_Region']].rename(
            columns={
                'Destination_Country':      'country_name',
                'Destination_Country_Code': 'country_code',
                'Destination_Region':       'region'
            }
        )

        all_countries = pd.concat([origin_countries, dest_countries]).drop_duplicates(subset='country_name')

        nodes = []
        for _, row in all_countries.iterrows():
            nodes.append({
                'id':           f"Country_{row['country_name']}",
                'country_name': row['country_name'],
                'country_code': row['country_code'],
                'region':       row['region'],
            })

        self.nodes['Country'] = nodes
        print(f"   Extracted {len(nodes)} Country nodes")
        return nodes

    def extract_product_category_nodes(self) -> List[Dict]:
        """
        Extract ProductCategory master nodes from unique Product_Category values.

        Properties extracted:
            category_name

        Returns:
            List of dicts, one per unique product category.
        """
        print("Extracting ProductCategory nodes...")

        nodes = []
        for category in self.df['Product_Category'].unique():
            nodes.append({
                'id':            f"Category_{category}",
                'category_name': category,
            })

        self.nodes['ProductCategory'] = nodes
        print(f"   Extracted {len(nodes)} ProductCategory nodes")
        return nodes

    def extract_transport_mode_nodes(self) -> List[Dict]:
        """
        Extract TransportMode master nodes from unique Transportation_Mode values.

        Properties extracted:
            mode_name

        Returns:
            List of dicts, one per unique transport mode.
        """
        print("Extracting TransportMode nodes...")

        nodes = []
        for mode in self.df['Transportation_Mode'].unique():
            nodes.append({
                'id':        f"Mode_{mode}",
                'mode_name': mode,
            })

        self.nodes['TransportMode'] = nodes
        print(f"   Extracted {len(nodes)} TransportMode nodes")
        return nodes

    def extract_disruption_type_nodes(self) -> List[Dict]:
        """
        Extract DisruptionType master nodes from unique Disruption_Event values,
        including 'No_Disruption' as an explicit node.

        Properties extracted:
            disruption_name

        Returns:
            List of dicts, one per unique disruption type.
        """
        print("Extracting DisruptionType nodes...")

        nodes = []
        for disruption in self.df['Disruption_Event'].unique():
            nodes.append({
                'id':              f"Disruption_{disruption}",
                'disruption_name': disruption,
            })

        self.nodes['DisruptionType'] = nodes
        print(f"   Extracted {len(nodes)} DisruptionType nodes")
        return nodes

    def extract_mitigation_action_nodes(self) -> List[Dict]:
        """
        Extract MitigationAction master nodes from unique Mitigation_Action_Taken
        values, with aggregated effectiveness metrics per action type.

        Properties extracted:
            action_name, avg_cost_impact, avg_delay_reduction

        Returns:
            List of dicts, one per unique mitigation action.
        """
        print("Extracting MitigationAction nodes...")

        grouped = self.df.groupby('Mitigation_Action_Taken').agg(
            avg_cost_impact=('Shipping_Cost_USD', 'mean'),
            avg_delay_reduction=('Delay_Days', 'mean')
        ).reset_index()

        nodes = []
        for _, row in grouped.iterrows():
            action_name = row['Mitigation_Action_Taken']
            nodes.append({
                'id':                 f"Action_{action_name}",
                'action_name':        action_name,
                'avg_cost_impact':    round(float(row['avg_cost_impact']), 2),
                'avg_delay_reduction': round(float(row['avg_delay_reduction']), 2),
            })

        self.nodes['MitigationAction'] = nodes
        print(f"   Extracted {len(nodes)} MitigationAction nodes")
        return nodes

    # =========================================================================
    # RELATIONSHIP EXTRACTION
    # =========================================================================

    def extract_operative_relationships(self) -> Dict[str, List[Dict]]:
        """
        Extract operative relationships — all centred on Order nodes.

        Relationships:
        - ORIGIN_FROM     (Order)-[:ORIGIN_FROM]->(City)
        - DESTINATION_TO  (Order)-[:DESTINATION_TO]->(City)
        - SHIPPED_VIA     (Order)-[:SHIPPED_VIA]->(Route)
        - TRANSPORTS      (Order)-[:TRANSPORTS]->(ProductCategory)  + weight_kg
        - USES_MODE       (Order)-[:USES_MODE]->(TransportMode)

        Returns:
            Dict mapping relationship type name to list of relationship dicts.
        """
        print("Extracting operative relationships...")

        origin_from = []
        destination_to = []
        shipped_via = []
        transports = []
        uses_mode = []

        for _, row in self.df.iterrows():
            order_id = row['Order_ID']

            origin_from.append({
                'from': f"Order_{order_id}",
                'to':   f"City_{row['Origin_City_Name']}",
            })

            destination_to.append({
                'from': f"Order_{order_id}",
                'to':   f"City_{row['Destination_City_Name']}",
            })

            shipped_via.append({
                'from': f"Order_{order_id}",
                'to':   f"Route_{row['Route_Type']}",
            })

            transports.append({
                'from':      f"Order_{order_id}",
                'to':        f"Category_{row['Product_Category']}",
                'weight_kg': int(row['Order_Weight_Kg']),
            })

            uses_mode.append({
                'from': f"Order_{order_id}",
                'to':   f"Mode_{row['Transportation_Mode']}",
            })

        rels = {
            'ORIGIN_FROM':    origin_from,
            'DESTINATION_TO': destination_to,
            'SHIPPED_VIA':    shipped_via,
            'TRANSPORTS':     transports,
            'USES_MODE':      uses_mode,
        }

        for name, rel_list in rels.items():
            print(f"   {name}: {len(rel_list)} relationships")

        self.relationships.update(rels)
        return rels

    def extract_risk_relationships(self) -> Dict[str, List[Dict]]:
        """
        Extract risk and response relationships.

        Relationships:
        - AFFECTED_BY    (Order)-[:AFFECTED_BY]->(DisruptionType)
        - MITIGATED_WITH (Order)-[:MITIGATED_WITH]->(MitigationAction)
        - HAS_RISK       (Order)-[:HAS_RISK]->(RiskAssessment)

        Returns:
            Dict mapping relationship type name to list of relationship dicts.
        """
        print("Extracting risk & response relationships...")

        affected_by = []
        mitigated_with = []
        has_risk = []

        for _, row in self.df.iterrows():
            order_id = row['Order_ID']

            affected_by.append({
                'from': f"Order_{order_id}",
                'to':   f"Disruption_{row['Disruption_Event']}",
            })

            mitigated_with.append({
                'from': f"Order_{order_id}",
                'to':   f"Action_{row['Mitigation_Action_Taken']}",
            })

            has_risk.append({
                'from': f"Order_{order_id}",
                'to':   f"Risk_{row['assessment_id']}",
            })

        rels = {
            'AFFECTED_BY':    affected_by,
            'MITIGATED_WITH': mitigated_with,
            'HAS_RISK':       has_risk,
        }

        for name, rel_list in rels.items():
            print(f"   {name}: {len(rel_list)} relationships")

        self.relationships.update(rels)
        return rels

    def extract_structural_relationships(self) -> Dict[str, List[Dict]]:
        """
        Extract structural relationships defining the topology of the logistics
        network, independent of individual shipments.

        Relationships:
        - LOCATED_IN   (City)-[:LOCATED_IN]->(Country)
        - CONNECTS     (Route)-[:CONNECTS]->(City)  + direction (origin|destination)
        - VULNERABLE_TO (Route)-[:VULNERABLE_TO]->(DisruptionType)
                        + frequency (int), severity (str, median delay_severity
                        of affected orders)

        Returns:
            Dict mapping relationship type name to list of relationship dicts.
        """
        print("Extracting structural relationships...")

        # --- LOCATED_IN ---
        origin_loc = self.df[['Origin_City_Name', 'Origin_Country']].rename(
            columns={'Origin_City_Name': 'city', 'Origin_Country': 'country'}
        )
        dest_loc = self.df[['Destination_City_Name', 'Destination_Country']].rename(
            columns={'Destination_City_Name': 'city', 'Destination_Country': 'country'}
        )
        city_country = pd.concat([origin_loc, dest_loc]).drop_duplicates()

        located_in = []
        for _, row in city_country.iterrows():
            located_in.append({
                'from': f"City_{row['city']}",
                'to':   f"Country_{row['country']}",
            })

        # --- CONNECTS ---
        origin_connects = self.df[['Route_Type', 'Origin_City_Name']].drop_duplicates().rename(
            columns={'Origin_City_Name': 'city'}
        )
        origin_connects['direction'] = 'origin'

        dest_connects = self.df[['Route_Type', 'Destination_City_Name']].drop_duplicates().rename(
            columns={'Destination_City_Name': 'city'}
        )
        dest_connects['direction'] = 'destination'

        connects = []
        for _, row in pd.concat([origin_connects, dest_connects]).iterrows():
            connects.append({
                'from':      f"Route_{row['Route_Type']}",
                'to':        f"City_{row['city']}",
                'direction': row['direction'],
            })

        # --- VULNERABLE_TO ---
        # Only for actual disruptions (exclude No_Disruption)
        disrupted = self.df[self.df['Disruption_Event'] != 'No_Disruption']

        severity_order = {'None': 0, 'Minor': 1, 'Moderate': 2, 'Severe': 3, 'Critical': 4}
        severity_reverse = {v: k for k, v in severity_order.items()}

        vulnerable_to = []
        grouped = disrupted.groupby(['Route_Type', 'Disruption_Event'])

        for (route, disruption), group in grouped:
            frequency = len(group)
            median_severity_num = group['delay_severity'].map(severity_order).median()
            severity = severity_reverse.get(round(median_severity_num), 'Moderate')

            vulnerable_to.append({
                'from':      f"Route_{route}",
                'to':        f"Disruption_{disruption}",
                'frequency': frequency,
                'severity':  severity,
            })

        rels = {
            'LOCATED_IN':    located_in,
            'CONNECTS':      connects,
            'VULNERABLE_TO': vulnerable_to,
        }

        for name, rel_list in rels.items():
            print(f"   {name}: {len(rel_list)} relationships")

        self.relationships.update(rels)
        return rels

    # =========================================================================
    # MAIN PIPELINE
    # =========================================================================

    def extract(self) -> Dict:
        """
        Execute the complete extraction pipeline: all nodes and relationships.

        Returns:
            Dict with two keys:
            {
                'nodes':         dict mapping node type -> list of node dicts,
                'relationships': dict mapping rel type  -> list of rel dicts
            }
        """
        print("=" * 60)
        print("STARTING KG EXTRACTION PIPELINE")
        print("=" * 60)

        # Nodes
        print("\n--- NODE EXTRACTION ---")
        self.extract_order_nodes()
        self.extract_risk_assessment_nodes()
        self.extract_route_nodes()
        self.extract_city_nodes()
        self.extract_country_nodes()
        self.extract_product_category_nodes()
        self.extract_transport_mode_nodes()
        self.extract_disruption_type_nodes()
        self.extract_mitigation_action_nodes()

        # Relationships
        print("\n--- RELATIONSHIP EXTRACTION ---")
        self.extract_operative_relationships()
        self.extract_risk_relationships()
        self.extract_structural_relationships()

        # Summary
        total_nodes = sum(len(v) for v in self.nodes.values())
        total_rels = sum(len(v) for v in self.relationships.values())

        print("\n" + "=" * 60)
        print("EXTRACTION COMPLETE")
        print("=" * 60)
        print(f"   Total nodes:         {total_nodes:,}")
        for node_type, node_list in self.nodes.items():
            print(f"      {node_type:<22} {len(node_list):>6,}")
        print(f"   Total relationships: {total_rels:,}")
        for rel_type, rel_list in self.relationships.items():
            print(f"      {rel_type:<22} {len(rel_list):>6,}")

        return {
            'nodes':         self.nodes,
            'relationships': self.relationships,
        }


# Example usage
if __name__ == "__main__":
    df_transformed = pd.read_csv(os.path.join(DATA_DIR, "data_transformed.csv"))
    print(f"Loaded {len(df_transformed)} rows from data_transformed.csv\n")

    extractor = KGExtractor(df_transformed)
    kg_data = extractor.extract()