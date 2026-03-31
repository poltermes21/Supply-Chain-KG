"""
KG Extractor Module

Reads the transformed dataset and extracts all nodes and relationships
needed to build the Knowledge Graph in Neo4j.
"""

import pandas as pd
import os
from typing import Dict, List
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

    # 1. NODE EXTRACTION

    def extract_order_nodes(self) -> List[Dict]:
        """
        Extract Order nodes — one per row.

        id = Order_ID (e.g. 'ORD-00BCB25B')
        """
        print("Extracting Order nodes...")

        order_cols = [
            'Order_ID', 'Order_Date',
            'Base_Lead_Time_Days', 'Scheduled_Lead_Time_Days',
            'Actual_Lead_Time_Days', 'Delay_Days',
            'Shipping_Cost_USD', 'Order_Weight_Kg',
            'Delivery_Status', 'cost_category',
            'is_delayed', 'is_disrupted',
            'delay_severity', 'lead_time_efficiency',
            'cost_per_kg', 'delay_ratio', 'cost_premium',
            'mitigation_effectiveness', 'mitigation_effective'
        ]

        nodes = []
        for _, row in self.df[order_cols].iterrows():
            nodes.append({
                'id':                       row['Order_ID'],
                'order_date':               row['Order_Date'].to_pydatetime().date(),
                'base_lead_time_days':      int(row['Base_Lead_Time_Days']),
                'scheduled_lead_time_days': int(row['Scheduled_Lead_Time_Days']),
                'actual_lead_time_days':    int(row['Actual_Lead_Time_Days']),
                'delay_days':               int(row['Delay_Days']),
                'shipping_cost_usd':        round(float(row['Shipping_Cost_USD']), 2),
                'order_weight_kg':          int(row['Order_Weight_Kg']),
                'delivery_status':          row['Delivery_Status'],
                'cost_category':            row['cost_category'],
                'is_delayed':               bool(row['is_delayed']),
                'is_disrupted':             bool(row['is_disrupted']),
                'delay_severity':           row['delay_severity'],
                'lead_time_efficiency':     round(float(row['lead_time_efficiency']), 2),
                'cost_per_kg':              round(float(row['cost_per_kg']), 2),
                'delay_ratio':              round(float(row['delay_ratio']), 2),
                'cost_premium':             round(float(row['cost_premium']), 2),
                'mitigation_effectiveness': row['mitigation_effectiveness'],   # ← nou
                'mitigation_effective':     bool(row['mitigation_effective'])
            })

        self.nodes['Order'] = nodes
        print(f"   Extracted {len(nodes)} Order nodes")
        return nodes

    def extract_risk_assessment_nodes(self) -> List[Dict]:
        """
        Extract RiskAssessment nodes — one per Order (1:1 via HAS_RISK).

        id = assessment_id (e.g. 'ORD-00BCB25B_risk')
        """
        print("Extracting RiskAssessment nodes...")

        risk_cols = [
            'assessment_id',
            'Geopolitical_Risk_Index', 'Weather_Severity_Index',
            'Inflation_Rate_Pct', 'combined_risk_score',
            'risk_level'
        ]

        nodes = []
        for _, row in self.df[risk_cols].iterrows():
            nodes.append({
                'id':                      row['assessment_id'],
                'geopolitical_risk_index': round(float(row['Geopolitical_Risk_Index']), 4),
                'weather_severity_index':  round(float(row['Weather_Severity_Index']), 2),
                'inflation_rate_pct':      round(float(row['Inflation_Rate_Pct']), 4),
                'combined_risk_score':     round(float(row['combined_risk_score']), 4),
                'risk_level':              row['risk_level']
            })

        self.nodes['RiskAssessment'] = nodes
        print(f"   Extracted {len(nodes)} RiskAssessment nodes")
        return nodes

    def extract_route_nodes(self) -> List[Dict]:
        """
        Extract Route master nodes.

        id = Route_Type (e.g. 'Pacific')
        """
        print("Extracting Route nodes...")

        nodes = []
        for route_type in self.df['Route_Type'].unique():
            nodes.append({
                'id': route_type,
            })

        self.nodes['Route'] = nodes
        print(f"   Extracted {len(nodes)} Route nodes")
        return nodes

    def extract_city_nodes(self) -> List[Dict]:
        """
        Extract City master nodes.

        id = city_name (e.g. 'Shanghai')
        """
        print("Extracting City nodes...")

        origin_cities = self.df[['Origin_City_Name']].rename(
            columns={'Origin_City_Name': 'city_name'}
        )
        dest_cities = self.df[['Destination_City_Name']].rename(
            columns={'Destination_City_Name': 'city_name'}
        )
        
        outbound_counts = self.df['Origin_City_Name'].value_counts()
        inbound_counts = self.df['Destination_City_Name'].value_counts()

        all_cities = pd.concat([origin_cities, dest_cities]).drop_duplicates(subset='city_name')

        nodes = []
        for city in all_cities['city_name']:
            outbound = outbound_counts.get(city, 0)
            inbound = inbound_counts.get(city, 0)

            if outbound > 0 and inbound > 0:
                role = 'H'  # Hub
            elif outbound > 0:
                role = 'O'  # Origin
            elif inbound > 0:
                role = 'D'  # Destination
            else:
                role = 'isolated'

            nodes.append({
                'id': city,
                'role': role,
                'outbound_degree': int(outbound),
                'inbound_degree': int(inbound)
            })

        self.nodes['City'] = nodes
        print(f"   Extracted {len(nodes)} City nodes")
        return nodes

    def extract_country_nodes(self) -> List[Dict]:
        """
        Extract Country master nodes.
        """
        print("Extracting Country nodes...")

        origin_countries = self.df[['Origin_Country', 'Origin_Country_Code', 'Origin_Region']].rename(
            columns={'Origin_Country': 'country_name', 'Origin_Country_Code': 'country_code', 'Origin_Region': 'region'}
        )
        dest_countries = self.df[['Destination_Country', 'Destination_Country_Code', 'Destination_Region']].rename(
            columns={'Destination_Country': 'country_name', 'Destination_Country_Code': 'country_code', 'Destination_Region': 'region'}
        )

        all_countries = pd.concat([origin_countries, dest_countries]).drop_duplicates(subset='country_code')

        nodes = []
        for _, row in all_countries.iterrows():
            nodes.append({
                'id':           row['country_code'],
                'country_name': row['country_name'],
                'region':       row['region'],
            })

        self.nodes['Country'] = nodes
        print(f"   Extracted {len(nodes)} Country nodes")
        return nodes

    def extract_product_category_nodes(self) -> List[Dict]:
        """
        Extract ProductCategory master nodes.

        id             = product_category_id (numeric: 0, 1, 2...)
        category_name  = Product_Category (e.g. 'Textiles')
        """
        print("Extracting ProductCategory nodes...")

        category_map = self.df[['product_category_id', 'Product_Category']].drop_duplicates()

        nodes = []
        for _, row in category_map.iterrows():
            nodes.append({
                'id':            int(row['product_category_id']),
                'name': row['Product_Category'],
            })

        self.nodes['ProductCategory'] = nodes
        print(f"   Extracted {len(nodes)} ProductCategory nodes")
        return nodes

    def extract_transport_mode_nodes(self) -> List[Dict]:
        """
        Extract TransportMode master nodes.

        id = Transportation_Mode (e.g. 'Air')
        """
        print("Extracting TransportMode nodes...")

        nodes = []
        for mode in self.df['Transportation_Mode'].unique():
            nodes.append({
                'id': mode,
            })

        self.nodes['TransportMode'] = nodes
        print(f"   Extracted {len(nodes)} TransportMode nodes")
        return nodes

    def extract_disruption_type_nodes(self) -> List[Dict]:
        """
        Extract DisruptionType master nodes.

        id             = disruption_id (numeric: 0, 1, 2...)
        disruption_name = normalized snake_case (e.g. 'port_congestion')
        display_name   = original Disruption_Event string (e.g. 'Port Congestion')
        """
        print("Extracting DisruptionType nodes...")

        disruption_map = self.df[['disruption_id', 'disruption_name', 'Disruption_Event']].drop_duplicates()

        nodes = []
        for _, row in disruption_map.iterrows():
            nodes.append({
                'id':              int(row['disruption_id']),
                'name': row['disruption_name'],
                'full_name':    row['Disruption_Event'],
            })

        self.nodes['DisruptionType'] = nodes
        print(f"   Extracted {len(nodes)} DisruptionType nodes")
        return nodes

    def extract_mitigation_action_nodes(self) -> List[Dict]:
        """
        Extract MitigationAction master nodes with aggregated effectiveness metrics.

        id                  = mitigation_action_id (numeric: 0, 1, 2...)
        action_name         = Mitigation_Action_Taken (e.g. 'Standard Shipping')
        avg_cost_impact     = average shipping cost for this mitigation
        avg_delay_reduction = average delay days for this mitigation
        """
        print("Extracting MitigationAction nodes...")

        grouped = self.df.groupby(['mitigation_action_id', 'Mitigation_Action_Taken']).agg(
            avg_cost_impact=('Shipping_Cost_USD', 'mean'),
            avg_delay_reduction=('Delay_Days', 'mean')
        ).reset_index()

        nodes = []
        for _, row in grouped.iterrows():
            nodes.append({
                'id':                  int(row['mitigation_action_id']),
                'name':         row['Mitigation_Action_Taken'],
                'avg_cost_impact':     round(float(row['avg_cost_impact']), 2),
                'avg_delay_reduction': round(float(row['avg_delay_reduction']), 2),
            })

        self.nodes['MitigationAction'] = nodes
        print(f"   Extracted {len(nodes)} MitigationAction nodes")
        return nodes

    # 2. RELATIONSHIP EXTRACTION

    def extract_operative_relationships(self) -> Dict[str, List[Dict]]:
        """
        Operative relationships centred on Order nodes.

        - ORIGIN_FROM    (Order)->(City)
        - DESTINATION_TO (Order)->(City)
        - SHIPPED_VIA    (Order)->(Route)
        - TRANSPORTS     (Order)->(ProductCategory)  + weight_kg
        - USES_MODE      (Order)->(TransportMode)
        """
        print("Extracting operative relationships...")

        origin_from    = []
        destination_to = []
        shipped_via    = []
        transports     = []
        uses_mode      = []

        for _, row in self.df.iterrows():
            order_id = row['Order_ID']

            origin_from.append({
                'from': order_id,
                'to':   row['Origin_City_Name'],
            })
            destination_to.append({
                'from': order_id,
                'to':   row['Destination_City_Name'],
            })
            shipped_via.append({
                'from': order_id,
                'to':   row['Route_Type'],
            })
            transports.append({
                'from':      order_id,
                'to':        int(row['product_category_id']),
                'weight_kg': int(row['Order_Weight_Kg']),
            })
            uses_mode.append({
                'from': order_id,
                'to':   row['Transportation_Mode'],
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
        Risk and response relationships.

        - AFFECTED_BY    (Order)->(DisruptionType)
        - MITIGATED_WITH (Order)->(MitigationAction)
        - HAS_RISK       (Order)->(RiskAssessment)
        """
        print("Extracting risk & response relationships...")

        affected_by    = []
        mitigated_with = []
        has_risk       = []

        for _, row in self.df.iterrows():
            order_id = row['Order_ID']

            affected_by.append({
                'from': order_id,
                'to':   int(row['disruption_id']),
            })
            mitigated_with.append({
                'from': order_id,
                'to':   int(row['mitigation_action_id']),
            })
            has_risk.append({
                'from': order_id,
                'to':   row['assessment_id'],
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
        Structural relationships defining logistics network topology.

        - LOCATED_IN    (City)->(Country)
        - CONNECTS      (Route)->(City)       + direction
        - VULNERABLE_TO (Route)->(DisruptionType) + frequency, severity
        """
        print("Extracting structural relationships...")

        # --- LOCATED_IN ---
        origin_loc = self.df[['Origin_City_Name', 'Origin_Country_Code']].rename(
            columns={'Origin_City_Name': 'city', 'Origin_Country_Code': 'country_code'}
        )
        dest_loc = self.df[['Destination_City_Name', 'Destination_Country_Code']].rename(
            columns={'Destination_City_Name': 'city', 'Destination_Country_Code': 'country_code'}
        )
        city_country = pd.concat([origin_loc, dest_loc]).drop_duplicates()

        located_in = []
        for _, row in city_country.iterrows():
            located_in.append({
                'from': row['city'],
                'to':   row['country_code'],
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
                'from':      row['Route_Type'],
                'to':        row['city'],
                'direction': row['direction'],
            })

        # --- VULNERABLE_TO ---
        disrupted = self.df[self.df['Disruption_Event'] != 'No_Disruption']

        severity_order   = {'none': 0, 'minor': 1, 'moderate': 2, 'severe': 3, 'critical': 4}
        severity_reverse = {v: k for k, v in severity_order.items()}

        vulnerable_to = []
        for (route, disruption_id), group in disrupted.groupby(['Route_Type', 'disruption_id']):
            frequency           = len(group)
            median_severity_num = group['delay_severity'].map(severity_order).median()
            severity            = severity_reverse.get(round(median_severity_num), 'moderate')

            vulnerable_to.append({
                'from':      route,
                'to':        int(disruption_id),
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
    
    def extract_city_flow_relationships(self) -> List[Dict]:
        """
        Analytical relationship layer:
        Aggregates Order-level flows into one CITY_FLOW relationship per OD pair.
        (City)-[:CITY_FLOW]->(City)
        """
        print("Extracting CITY_FLOW analytical relationships...")

        required_cols = [
            'Origin_City_Name',
            'Destination_City_Name',
            'Route_Type',
            'Transportation_Mode',
            'Shipping_Cost_USD',
            'Actual_Lead_Time_Days',
            'Delay_Days',
            'Order_Weight_Kg',
            'combined_risk_score',
            'is_delayed',
            'is_disrupted'
        ]

        missing = [c for c in required_cols if c not in self.df.columns]
        if missing:
            raise ValueError(f"Missing columns for CITY_FLOW extraction: {missing}")

        city_flow = []

        grouped = self.df.groupby(
            ['Origin_City_Name', 'Destination_City_Name'],
            dropna=False
        )

        for (origin, destination), group in grouped:
            route_counts = group['Route_Type'].value_counts()
            mode_counts = group['Transportation_Mode'].value_counts()

            city_flow.append({
                'from': origin,
                'to': destination,

                'shipments': int(len(group)),
                'total_weight_kg': int(group['Order_Weight_Kg'].sum()),

                'route_count': int(group['Route_Type'].nunique()),
                'routes_used': sorted(group['Route_Type'].dropna().unique().tolist()),
                'primary_route': route_counts.idxmax(),
                'primary_route_share_pct': round(float(route_counts.iloc[0] / len(group) * 100), 2),

                'dominant_mode': mode_counts.idxmax(),
                'air_share_pct': round(float(group['Transportation_Mode'].eq('Air').mean() * 100), 2),

                'avg_cost_usd': round(float(group['Shipping_Cost_USD'].mean()), 2),
                'avg_lead_time_days': round(float(group['Actual_Lead_Time_Days'].mean()), 2),
                'avg_delay_days': round(float(group['Delay_Days'].mean()), 2),

                'delay_rate_pct': round(float(group['is_delayed'].mean() * 100), 2),
                'disrupted_rate_pct': round(float(group['is_disrupted'].mean() * 100), 2),
                'avg_combined_risk_score': round(float(group['combined_risk_score'].mean()), 4),
            })

        self.relationships['CITY_FLOW'] = city_flow
        print(f"   CITY_FLOW: {len(city_flow)} relationships")
        return city_flow

    # MAIN PIPELINE

    def extract(self) -> Dict:
        """
        Execute the complete extraction pipeline.

        Returns:
            {
                'nodes':         dict mapping node type -> list of node dicts,
                'relationships': dict mapping rel type  -> list of rel dicts
            }
        """
        print("=" * 60)
        print("STARTING KG EXTRACTION PIPELINE")
        print("=" * 60)

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

        print("\n--- RELATIONSHIP EXTRACTION ---")
        self.extract_operative_relationships()
        self.extract_risk_relationships()
        self.extract_structural_relationships()
        self.extract_city_flow_relationships()

        total_nodes = sum(len(v) for v in self.nodes.values())
        total_rels  = sum(len(v) for v in self.relationships.values())

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


if __name__ == "__main__":
    df_transformed = pd.read_csv(os.path.join(DATA_DIR, "data_transformedv2.csv"))
    print(f"Loaded {len(df_transformed)} rows from data_transformed.csv\n")

    extractor = KGExtractor(df_transformed)
    kg_data = extractor.extract()