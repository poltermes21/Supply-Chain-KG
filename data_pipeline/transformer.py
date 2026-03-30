"""
Data Transformation Module - Supply Chain Resilience Dataset

Creates derived fields, composite metrics, and classifications.
Transforms the cleaned dataset into an enriched version ready for KG entity extraction.
"""
import pandas as pd
import numpy as np
import os
import re
from typing import Dict, Tuple

class DataTransformer:
    """
    Transform cleaned data by creating derived fields and metrics.
    Does NOT validate or clean - assumes input is already cleaned by DataCleaner.
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize the DataTransformer.
        
        Args:
            df: Cleaned dataframe from DataCleaner
        """
        self.df = df.copy()
        self.transformation_stats = {}
        
        # ID mappings for entities
        self.category_id_map = {}
        self.disruption_id_map = {}
        self.mitigation_id_map = {}
    
    # 0. ID NORMALIZATION
    
    @staticmethod
    def normalize_disruption_name(value: str) -> str:
        """
        Normalize a Disruption_Event string to a short, stable snake_case name.
        Parenthetical details are stripped to keep names concise and query-friendly.
        
        Examples:
            'No_Disruption' -> 'no_disruption'
            'Port Congestion' -> 'port_congestion'
            'Geopolitical Conflict (Route Diversion)' -> 'geopolitical_conflict'
            'Severe Weather (Typhoon/Storm)' -> 'severe_weather'
        """
        value = re.sub(r'\(.*?\)', '', value)
        value = value.lower().strip()
        value = re.sub(r'[\s_]+', '_', value)
        value = value.strip('_')
        return value
    
    def create_numeric_ids(self):
        """
        Create numeric IDs for Product_Category, Disruption_Event, and Mitigation_Action_Taken.
        
        IDs start at 0 for the first element.
        For disruptions, 'No_Disruption' is always assigned ID 0.
        
        Adds columns:
            - product_category_id: 0, 1, 2...
            - disruption_id: 0, 1, 2... (0 = No_Disruption)
            - mitigation_action_id: 0, 1, 2...
        """
        print("Creating numeric IDs for entities...")
        
        # Product Category IDs (0-indexed, alphabetically sorted)
        unique_categories = sorted(self.df['Product_Category'].unique())
        self.category_id_map = {cat: idx for idx, cat in enumerate(unique_categories)}
        self.df['product_category_id'] = self.df['Product_Category'].map(self.category_id_map)
        print(f"  Product Categories: {len(self.category_id_map)} unique")
        for cat, cat_id in sorted(self.category_id_map.items(), key=lambda x: x[1]):
            print(f"    {cat_id}: {cat}")
        
        # Disruption Type IDs (0-indexed, No_Disruption = 0, rest alphabetically)
        unique_disruptions = sorted(self.df['Disruption_Event'].unique())
        
        # Ensure No_Disruption gets ID 0
        if 'No_Disruption' in unique_disruptions:
            unique_disruptions.remove('No_Disruption')
            unique_disruptions = ['No_Disruption'] + unique_disruptions
        
        self.disruption_id_map = {dis: idx for idx, dis in enumerate(unique_disruptions)}
        self.df['disruption_id'] = self.df['Disruption_Event'].map(self.disruption_id_map)
        print(f"  Disruption Types: {len(self.disruption_id_map)} unique")
        for dis, dis_id in sorted(self.disruption_id_map.items(), key=lambda x: x[1]):
            print(f"    {dis_id}: {dis}")
        
        # Mitigation Action IDs (0-indexed, alphabetically sorted)
        unique_mitigations = sorted(self.df['Mitigation_Action_Taken'].unique())
        self.mitigation_id_map = {mit: idx for idx, mit in enumerate(unique_mitigations)}
        self.df['mitigation_action_id'] = self.df['Mitigation_Action_Taken'].map(self.mitigation_id_map)
        print(f"  Mitigation Actions: {len(self.mitigation_id_map)} unique")
        for mit, mit_id in sorted(self.mitigation_id_map.items(), key=lambda x: x[1]):
            print(f"    {mit_id}: {mit}")
        
        # Store mappings in stats
        self.transformation_stats['id_mappings'] = {
            'product_category': self.category_id_map,
            'disruption_type': self.disruption_id_map,
            'mitigation_action': self.mitigation_id_map
        }
    
    def create_disruption_name(self):
        """
        Add disruption_name column: normalized snake_case version of Disruption_Event.
        Used as a readable identifier for DisruptionType nodes in the KG.
        """
        print("Creating disruption_name normalization...")
        self.df['disruption_name'] = self.df['Disruption_Event'].apply(self.normalize_disruption_name)
        
        # Create mapping for documentation
        unique_mapping = dict(zip(
            self.df['Disruption_Event'].unique(),
            self.df['disruption_name'].unique()
        ))
        print(f"  Mapping: {unique_mapping}")
    
    # 1. CLASSIFICATION FIELDS
    
    def create_delay_severity(self):
        """
        Categorize Delay_Days into severity levels.
        
        Thresholds:
            - None: 0 days
            - Minor: 1-3 days
            - Moderate: 4-7 days
            - Severe: 8-14 days
            - Critical: >14 days
        """
        print("Creating delay_severity classification...")
        
        conditions = [
            self.df['Delay_Days'] == 0,
            self.df['Delay_Days'] <= 3,
            self.df['Delay_Days'] <= 7,
            self.df['Delay_Days'] <= 14,
            self.df['Delay_Days'] > 14
        ]
        choices = ['none', 'minor', 'moderate', 'severe', 'critical']
        
        self.df['delay_severity'] = np.select(conditions, choices, default='unknown')
        
        severity_counts = self.df['delay_severity'].value_counts()
        self.transformation_stats['delay_severity_distribution'] = severity_counts.to_dict()
        print(f"  Distribution: {severity_counts.to_dict()}")
    
    def create_risk_level(self):
        """
        Compute combined_risk_score and classify into risk levels.
        
        Formula (weighted average, result normalized to [0, 1]):
            combined_risk_score = Geopolitical_Risk_Index * 0.6 + (Weather_Severity_Index / 10) * 0.4
        
        Thresholds:
            - low: combined_risk_score < 0.3
            - medium: 0.3 <= combined_risk_score < 0.6
            - high: 0.6 <= combined_risk_score < 0.8
            - critical: combined_risk_score >= 0.8
        """
        print("Creating risk_level classification...")
        
        weather_normalized = self.df['Weather_Severity_Index'] / 10.0
        self.df['combined_risk_score'] = (
            self.df['Geopolitical_Risk_Index'] * 0.6 + 
            weather_normalized * 0.4
        ).round(4)
        
        conditions = [
            self.df['combined_risk_score'] < 0.3,
            self.df['combined_risk_score'] < 0.6,
            self.df['combined_risk_score'] < 0.8,
            self.df['combined_risk_score'] >= 0.8
        ]
        choices = ['low', 'medium', 'high', 'critical']
        
        self.df['risk_level'] = np.select(conditions, choices, default='unknown')
        
        risk_counts = self.df['risk_level'].value_counts()
        self.transformation_stats['risk_level_distribution'] = risk_counts.to_dict()
        print(f"  Distribution: {risk_counts.to_dict()}")
    
    def create_cost_category(self):
        """
        Categorize Shipping_Cost_USD into cost tiers using quartiles 
        computed WITHIN each Product_Category.
        
        Thresholds per category:
            - budget: <= Q1 (bottom 25%)
            - standard: Q1-Q2 (25-50%)
            - premium: Q2-Q3 (50-75%)
            - emergency: > Q3 (top 25%) - correlates with disruption response
        """
        print("Creating cost_category classification (per product category)...")
        
        self.df['cost_category'] = 'unknown'
        category_thresholds = {}
        
        for category in self.df['Product_Category'].unique():
            mask = self.df['Product_Category'] == category
            cat_costs = self.df.loc[mask, 'Shipping_Cost_USD']
            
            q1 = cat_costs.quantile(0.25)
            q2 = cat_costs.quantile(0.50)
            q3 = cat_costs.quantile(0.75)
            
            conditions = [
                cat_costs <= q1,
                cat_costs <= q2,
                cat_costs <= q3,
                cat_costs > q3
            ]
            choices = ['budget', 'standard', 'premium', 'emergency']
            
            self.df.loc[mask, 'cost_category'] = np.select(conditions, choices, default='unknown')
            
            category_thresholds[category] = {
                'q1_budget': float(q1),
                'q2_standard': float(q2),
                'q3_premium': float(q3)
            }
            print(f"  {category}: budget<${q1:.0f}, standard<${q2:.0f}, premium<${q3:.0f}")
        
        self.transformation_stats['cost_thresholds_by_category'] = category_thresholds
    
    # 2. BOOLEAN FLAGS
    
    def create_boolean_flags(self):
        """
        Create simple boolean flags for graph filtering.
        
        Flags created:
            - is_disrupted: True if a disruption event occurred (Disruption_Event != 'No_Disruption')
            - is_delayed: True if the order was delivered late (Delivery_Status == 'Late')
        """
        print("Creating boolean flags...")
        
        self.df['is_disrupted'] = self.df['Disruption_Event'] != 'No_Disruption'
        self.df['is_delayed'] = self.df['Delivery_Status'] == 'Late'
        
        self.transformation_stats['flags'] = {
            'disrupted_orders': int(self.df['is_disrupted'].sum()),
            'delayed_orders': int(self.df['is_delayed'].sum())
        }
        
        print(f"  Disrupted: {self.df['is_disrupted'].sum()}, Delayed: {self.df['is_delayed'].sum()}")
    
    # 3. CALCULATED METRICS
    
    def create_efficiency_metrics(self):
        """
        Create efficiency and performance metrics for Order nodes.
        
        Metrics created:
            - lead_time_efficiency (%): (Scheduled - Actual) / Scheduled * 100
            - cost_per_kg (USD/kg): Shipping_Cost_USD / Order_Weight_Kg
            - delay_ratio (%): Delay_Days / Scheduled_Lead_Time_Days * 100
        """
        print("Creating efficiency metrics...")
        
        self.df['lead_time_efficiency'] = (
            (self.df['Scheduled_Lead_Time_Days'] - self.df['Actual_Lead_Time_Days']) / 
            self.df['Scheduled_Lead_Time_Days'] * 100
        ).round(2)
        
        self.df['cost_per_kg'] = (
            self.df['Shipping_Cost_USD'] / self.df['Order_Weight_Kg']
        ).round(2)
        
        self.df['delay_ratio'] = (
            self.df['Delay_Days'] / self.df['Scheduled_Lead_Time_Days'] * 100
        ).round(2)
        
        print(f"  lead_time_efficiency: mean={self.df['lead_time_efficiency'].mean():.2f}%")
        print(f"  cost_per_kg: mean=${self.df['cost_per_kg'].mean():.2f}")
        print(f"  delay_ratio: mean={self.df['delay_ratio'].mean():.2f}%")
    
    def create_resilience_metrics(self):
        """
        Create metrics specifically for resilience analysis.

        Metrics created:
            - mitigation_effectiveness (str): 4-level classification of mitigation outcome
            - mitigation_effective (bool): True if fully or partially effective
            - cost_premium (%): (cost - avg_normal_cost) / avg_normal_cost * 100
            - route_segment (str): "{Origin_Region}_to_{Destination_Region}"
        """
        print("Creating resilience metrics...")

        conditions = [
            ~self.df['is_disrupted'],
            self.df['is_disrupted'] & ~self.df['is_delayed'],
            self.df['is_disrupted'] & self.df['is_delayed'] & (self.df['delay_severity'] == 'minor'),
            self.df['is_disrupted'] & self.df['is_delayed'] & ~(self.df['delay_severity'] == 'minor'),
        ]
        choices = [
            'not_applicable',
            'fully_effective',
            'partially_effective',
            'not_effective',
        ]
        self.df['mitigation_effectiveness'] = np.select(conditions, choices, default='unknown')

        self.df['mitigation_effective'] = self.df['mitigation_effectiveness'].isin(
            ['fully_effective', 'partially_effective']
        )

        self.df['route_segment'] = (
            self.df['Origin_Region'] + '_to_' + self.df['Destination_Region']
        )
        
                # 1. Crear weight buckets
        self.df['weight_bucket'] = pd.qcut(
            self.df['Order_Weight_Kg'], 
            q=4, 
            labels=False, 
            duplicates='drop'
        )

        # 2. Baseline segmentat (només no disruptives)
        baseline = (
            self.df[~self.df['is_disrupted']]
            .groupby(['route_segment', 'Transportation_Mode', 'weight_bucket'])['Shipping_Cost_USD']
            .median() 
        )

        # 3. Assignar baseline a cada fila
        self.df = self.df.join(
            baseline,
            on=['route_segment', 'Transportation_Mode', 'weight_bucket'],
            rsuffix='_baseline'
        )

        # 4. Cost premium
        self.df['cost_premium'] = (
            (self.df['Shipping_Cost_USD'] - self.df['Shipping_Cost_USD_baseline']) /
            self.df['Shipping_Cost_USD_baseline'] * 100
        )

        self.transformation_stats['resilience'] = {
            'mitigation_effectiveness_distribution': self.df['mitigation_effectiveness'].value_counts().to_dict(),
            'effective_mitigations': int(self.df['mitigation_effective'].sum()),
            'unique_route_segments': int(self.df['route_segment'].nunique())
        }

        print(f"  Effectiveness distribution: {self.df['mitigation_effectiveness'].value_counts().to_dict()}")
        print(f"  Effective mitigations (fully + partially): {self.df['mitigation_effective'].sum()}")
        print(f"  Avg cost premium disrupted orders: {self.df[self.df['is_disrupted']]['cost_premium'].mean():.2f}%")
    
    # 4. ENTITY PREPARATION
    
    def create_risk_assessment_id(self):
        """
        Generate the assessment_id for RiskAssessment nodes in the Knowledge Graph.
        Format: "{Order_ID}_risk"
        """
        print("Creating risk_assessment_id...")
        
        self.df['assessment_id'] = self.df['Order_ID'] + '_risk'
        unique_ids = self.df['assessment_id'].nunique()
        
        print(f"  Generated {unique_ids} unique assessment IDs")
        self.transformation_stats['assessment_ids_created'] = unique_ids
    
    def prepare_entity_columns(self):
        """
        Validate that all entity identifier columns are present and ready 
        for KG node extraction.
        
        Node types and their source columns (value used directly as node id):
            - Order: Order_ID
            - RiskAssessment: assessment_id
            - Route: Route_Type
            - City: Origin_City_Name / Destination_City_Name
            - Country: Origin_Country / Destination_Country
            - ProductCategory: product_category_id (numeric)
            - TransportMode: Transportation_Mode
            - DisruptionType: disruption_id (numeric)
            - MitigationAction: mitigation_action_id (numeric)
        """
        print("Validating entity columns...")
        
        entity_columns = {
            'Order': 'Order_ID',
            'RiskAssessment': 'assessment_id',
            'Route': 'Route_Type',
            'Origin_City': 'Origin_City_Name',
            'Dest_City': 'Destination_City_Name',
            'Origin_Country': 'Origin_Country',
            'Dest_Country': 'Destination_Country',
            'ProductCategory': 'product_category_id',
            'TransportMode': 'Transportation_Mode',
            'DisruptionType': 'disruption_id',
            'MitigationAction': 'mitigation_action_id'
        }
        
        entity_stats = {}
        for entity_name, col_name in entity_columns.items():
            unique_count = self.df[col_name].nunique()
            null_count = self.df[col_name].isna().sum()
            entity_stats[entity_name] = {
                'column': col_name,
                'unique_values': int(unique_count),
                'nulls': int(null_count)
            }
            print(f"  {entity_name}: {unique_count} unique values (nulls: {null_count})")
        
        self.transformation_stats['entities'] = entity_stats
    
    # MAIN PIPELINE
    
    def transform(self) -> Tuple[pd.DataFrame, Dict]:
        """
        Execute the complete transformation pipeline.
        
        Steps:
            0. ID normalization (numeric IDs + disruption_name)
            1. Classification fields (delay_severity, risk_level, cost_category)
            2. Boolean flags (is_disrupted, is_delayed)
            3. Efficiency metrics (lead_time_efficiency, cost_per_kg, delay_ratio)
            4. Resilience metrics (mitigation_effective, cost_premium, route_segment)
            5. Risk assessment ID (assessment_id)
            6. Entity validation (presence and null check for all KG node columns)
        """
        print("="*60)
        print("STARTING DATA TRANSFORMATION PIPELINE")
        print("="*60)
        
        original_cols = len(self.df.columns)
        
        print("\n--- STEP 0: ID NORMALIZATION ---")
        self.create_numeric_ids()  # Create numeric IDs first
        self.create_disruption_name()
        
        print("\n--- STEP 1: CLASSIFICATION FIELDS ---")
        self.create_delay_severity()
        self.create_risk_level()
        self.create_cost_category()
        
        print("\n--- STEP 2: BOOLEAN FLAGS ---")
        self.create_boolean_flags()
        
        print("\n--- STEP 3: EFFICIENCY METRICS ---")
        self.create_efficiency_metrics()
        
        print("\n--- STEP 4: RESILIENCE METRICS ---")
        self.create_resilience_metrics()
        
        print("\n--- STEP 5: RISK ASSESSMENT ID ---")
        self.create_risk_assessment_id()
        
        print("\n--- STEP 6: ENTITY VALIDATION ---")
        self.prepare_entity_columns()
        
        new_cols = len(self.df.columns)
        self.transformation_stats['columns'] = {
            'original': original_cols,
            'final': new_cols,
            'added': new_cols - original_cols
        }
        
        print("\n" + "="*60)
        print("TRANSFORMATION COMPLETE")
        print(f"Original columns: {original_cols} -> Final: {new_cols} (+{new_cols - original_cols})")
        print("="*60)
        
        return self.df, self.transformation_stats
    
    def save_output(self, output_dir: str = "data", filename: str = "data_transformedv2.csv"):
        """Save transformed dataset and stats to disk."""
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        self.df.to_csv(output_path, index=False)
        
        import json
        stats_path = os.path.join(output_dir, "transformation_stats.json")
        with open(stats_path, 'w') as f:
            json.dump(self.transformation_stats, f, indent=2)
        
        print(f"\nSaved to {output_path} | Stats to {stats_path}")
    
    def get_new_columns(self) -> list:
        """Return list of columns added by the transformer."""
        new_cols = []
        
        # Get all current columns
        all_cols = set(self.df.columns)
        
        # These are the columns we expect to add
        expected_new_cols = [
            # Numeric IDs
            'product_category_id',
            'disruption_id',
            'mitigation_action_id',
            # Name normalization
            'disruption_name',
            # Classifications
            'delay_severity',
            'risk_level',
            'combined_risk_score',
            'cost_category',
            # Boolean flags
            'is_disrupted',
            'is_delayed',
            # Efficiency metrics
            'lead_time_efficiency',
            'cost_per_kg',
            'delay_ratio',
            # Resilience metrics
            'mitigation_effectiveness'
            'mitigation_effective',
            'cost_premium',
            'route_segment',
            # Entity IDs
            'assessment_id',
        ]
        
        # Only return columns that actually exist in the dataframe
        for col in expected_new_cols:
            if col in all_cols:
                new_cols.append(col)
        
        return new_cols


if __name__ == "__main__":
    from settings import DATA_DIR
    
    df_cleaned = pd.read_csv(os.path.join(DATA_DIR, "data_cleanedv2.csv"))
    print(f"Loaded {len(df_cleaned)} rows from data_cleaned.csv")
    
    transformer = DataTransformer(df_cleaned)
    df_transformed, stats = transformer.transform()
    transformer.save_output()
    
    print("\n" + "="*60)
    print("NEW COLUMNS ADDED")
    print("="*60)
    for col in transformer.get_new_columns():
        print(f"  - {col}")