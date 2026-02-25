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

    # 0. ID NORMALIZATION

    @staticmethod
    def normalize_disruption_id(value: str) -> str:
        """
        Normalize a Disruption_Event string to a short, stable snake_case id.
        Parenthetical details are stripped to keep ids concise and query-friendly.

        Examples:
            'No_Disruption'                           -> 'no_disruption'
            'Port Congestion'                         -> 'port_congestion'
            'Geopolitical Conflict (Route Diversion)' -> 'geopolitical_conflict'
            'Severe Weather (Typhoon/Storm)'          -> 'severe_weather'
        """
        value = re.sub(r'\(.*?\)', '', value)
        value = value.lower().strip()
        value = re.sub(r'[\s_]+', '_', value)
        value = value.strip('_')
        return value

    def create_disruption_id(self):
        """
        Add disruption_id column: normalized snake_case version of Disruption_Event.
        Used as the node id for DisruptionType nodes in the KG.
        """
        print("Creating disruption_id normalization...")
        self.df['disruption_id'] = self.df['Disruption_Event'].apply(self.normalize_disruption_id)
        print(f"   Mapping: {dict(zip(self.df['Disruption_Event'].unique(), self.df['disruption_id'].unique()))}")


    # 1. CLASSIFICATION FIELDS
    
    def create_delay_severity(self):
        """
        Categorize Delay_Days into severity levels.

        Thresholds:
        - None:     0 days
        - Minor:    1-3 days
        - Moderate: 4-7 days
        - Severe:   8-14 days
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
        print(f"   Distribution: {severity_counts.to_dict()}")
    
    def create_risk_level(self):
        """
        Compute combined_risk_score and classify into risk levels.

        Formula (weighted average, result normalized to [0, 1]):
            combined_risk_score = Geopolitical_Risk_Index * 0.6
                                 + (Weather_Severity_Index / 10) * 0.4

        Thresholds:
        - low:      combined_risk_score < 0.3
        - medium:   0.3 <= combined_risk_score < 0.6
        - high:     0.6 <= combined_risk_score < 0.8
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
        print(f"   Distribution: {risk_counts.to_dict()}")
    
    def create_cost_category(self):
        """
        Categorize Shipping_Cost_USD into cost tiers using quartiles computed
        WITHIN each Product_Category.

        Thresholds per category:
        - budget:    <= Q1  (bottom 25%)
        - standard:  Q1-Q2  (25-50%)
        - premium:   Q2-Q3  (50-75%)
        - emergency: > Q3   (top 25%) - correlates with disruption response
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
                'q1_budget':   float(q1),
                'q2_standard': float(q2),
                'q3_premium':  float(q3)
            }
            print(f"   {category}: budget<${q1:.0f}, standard<${q2:.0f}, premium<${q3:.0f}")
        
        self.transformation_stats['cost_thresholds_by_category'] = category_thresholds
    
    # 2. BOOLEAN FLAGS
    
    def create_boolean_flags(self):
        """
        Create simple boolean flags for graph filtering.

        Flags created:
        - is_disrupted:   True if a disruption event occurred
                          (Disruption_Event != 'No_Disruption')
        - is_delayed:     True if the order was delivered late
                          (Delivery_Status == 'Late')
        - is_mitigated:   True if a special mitigation action was applied
                          (Mitigation_Action_Taken != 'Standard Shipping')
        - is_air_freight: True if transported by air
        """
        print("Creating boolean flags...")
        
        self.df['is_disrupted']   = self.df['Disruption_Event'] != 'No_Disruption'
        self.df['is_delayed']     = self.df['Delivery_Status'] == 'Late'
        self.df['is_mitigated']   = self.df['Mitigation_Action_Taken'] != 'Standard Shipping'
        self.df['is_air_freight'] = self.df['Transportation_Mode'] == 'Air'
        
        self.transformation_stats['flags'] = {
            'disrupted_orders': int(self.df['is_disrupted'].sum()),
            'delayed_orders':   int(self.df['is_delayed'].sum()),
            'mitigated_orders': int(self.df['is_mitigated'].sum())
        }
        print(f"   Disrupted: {self.df['is_disrupted'].sum()}, Delayed: {self.df['is_delayed'].sum()}, Mitigated: {self.df['is_mitigated'].sum()}")
    
    # 3. CALCULATED METRICS
    
    def create_efficiency_metrics(self):
        """
        Create efficiency and performance metrics for Order nodes.

        Metrics created:
        - lead_time_efficiency (%): (Scheduled - Actual) / Scheduled * 100
        - cost_per_kg (USD/kg):     Shipping_Cost_USD / Order_Weight_Kg
        - delay_ratio (%):          Delay_Days / Scheduled_Lead_Time_Days * 100
        """
        print("Creating efficiency metrics...")
        
        self.df['lead_time_efficiency'] = (
            (self.df['Scheduled_Lead_Time_Days'] - self.df['Actual_Lead_Time_Days']) 
            / self.df['Scheduled_Lead_Time_Days'] * 100
        ).round(2)
        
        self.df['cost_per_kg'] = (
            self.df['Shipping_Cost_USD'] / self.df['Order_Weight_Kg']
        ).round(2)
        
        self.df['delay_ratio'] = (
            self.df['Delay_Days'] / self.df['Scheduled_Lead_Time_Days'] * 100
        ).round(2)
        
        print(f"   lead_time_efficiency: mean={self.df['lead_time_efficiency'].mean():.2f}%")
        print(f"   cost_per_kg: mean=${self.df['cost_per_kg'].mean():.2f}")
        print(f"   delay_ratio: mean={self.df['delay_ratio'].mean():.2f}%")
    
    def create_resilience_metrics(self):
        """
        Create metrics specifically for resilience analysis.

        Metrics created:
        - mitigation_effective (bool): is_disrupted AND NOT is_delayed
        - cost_premium (%):            (cost - avg_normal_cost) / avg_normal_cost * 100
        - route_segment (str):         "{Origin_Region}_to_{Destination_Region}"
        """
        print("Creating resilience metrics...")
        
        self.df['mitigation_effective'] = (
            self.df['is_disrupted'] & ~self.df['is_delayed']
        )
        
        avg_normal_cost = self.df[~self.df['is_disrupted']]['Shipping_Cost_USD'].mean()
        self.df['cost_premium'] = (
            (self.df['Shipping_Cost_USD'] - avg_normal_cost) / avg_normal_cost * 100
        ).round(2)
        
        self.df['route_segment'] = (
            self.df['Origin_Region'] + '_to_' + self.df['Destination_Region']
        )
        
        self.transformation_stats['resilience'] = {
            'effective_mitigations':  int(self.df['mitigation_effective'].sum()),
            'unique_route_segments':  int(self.df['route_segment'].nunique())
        }
        print(f"   Effective mitigations: {self.df['mitigation_effective'].sum()}")
        print(f"   Avg cost premium disrupted orders: {self.df[self.df['is_disrupted']]['cost_premium'].mean():.2f}%")

    # 4. ENTITY PREPARATION

    def create_risk_assessment_id(self):
        """
        Generate the assessment_id for RiskAssessment nodes in the Knowledge Graph.
        Format: "{Order_ID}_risk"
        """
        print("Creating risk_assessment_id...")
        
        self.df['assessment_id'] = self.df['Order_ID'] + '_risk'
        
        unique_ids = self.df['assessment_id'].nunique()
        print(f"   Generated {unique_ids} unique assessment IDs")
        self.transformation_stats['assessment_ids_created'] = unique_ids
    
    def prepare_entity_columns(self):
        """
        Validate that all entity identifier columns are present and ready for
        KG node extraction.

        Node types and their source columns (value used directly as node id):
        - Order:            Order_ID
        - RiskAssessment:   assessment_id
        - Route:            Route_Type
        - City:             Origin_City_Name / Destination_City_Name
        - Country:          Origin_Country / Destination_Country
        - ProductCategory:  Product_Category
        - TransportMode:    Transportation_Mode
        - DisruptionType:   disruption_id  (normalized from Disruption_Event)
        - MitigationAction: Mitigation_Action_Taken
        """
        print("Validating entity columns...")
        
        entity_columns = {
            'Order':            'Order_ID',
            'RiskAssessment':   'assessment_id',
            'Route':            'Route_Type',
            'Origin_City':      'Origin_City_Name',
            'Dest_City':        'Destination_City_Name',
            'Origin_Country':   'Origin_Country',
            'Dest_Country':     'Destination_Country',
            'ProductCategory':  'Product_Category',
            'TransportMode':    'Transportation_Mode',
            'DisruptionType':   'disruption_id',
            'MitigationAction': 'Mitigation_Action_Taken'
        }
        
        entity_stats = {}
        for entity_name, col_name in entity_columns.items():
            unique_count = self.df[col_name].nunique()
            null_count   = self.df[col_name].isna().sum()
            entity_stats[entity_name] = {
                'column':        col_name,
                'unique_values': int(unique_count),
                'nulls':         int(null_count)
            }
            print(f"   {entity_name}: {unique_count} unique values (nulls: {null_count})")
        
        self.transformation_stats['entities'] = entity_stats
    
    # MAIN PIPELINNE
    
    def transform(self) -> Tuple[pd.DataFrame, Dict]:
        """
        Execute the complete transformation pipeline.

        Steps:
            0. ID normalization       (disruption_id)
            1. Classification fields  (delay_severity, risk_level, cost_category)
            2. Boolean flags          (is_disrupted, is_delayed, is_mitigated, is_air_freight)
            3. Efficiency metrics     (lead_time_efficiency, cost_per_kg, delay_ratio)
            4. Resilience metrics     (mitigation_effective, cost_premium, route_segment)
            5. Risk assessment ID     (assessment_id)
            6. Entity validation      (presence and null check for all KG node columns)
        """
        print("="*60)
        print("STARTING DATA TRANSFORMATION PIPELINE")
        print("="*60)
        
        original_cols = len(self.df.columns)

        print("\n--- STEP 0: ID NORMALIZATION ---")
        self.create_disruption_id()
        
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
            'final':    new_cols,
            'added':    new_cols - original_cols
        }
        
        print("\n" + "="*60)
        print("TRANSFORMATION COMPLETE")
        print(f"Original columns: {original_cols} -> Final: {new_cols} (+{new_cols - original_cols})")
        print("="*60)
        
        return self.df, self.transformation_stats
    
    def save_output(self, output_dir: str = "data", filename: str = "data_transformed.csv"):
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
        return [
            # ID normalization
            'disruption_id',
            # Classifications
            'delay_severity',
            'risk_level',
            'combined_risk_score',
            'cost_category',
            # Boolean flags
            'is_disrupted',
            'is_delayed',
            'is_mitigated',
            'is_air_freight',
            # Efficiency metrics
            'lead_time_efficiency',
            'cost_per_kg',
            'delay_ratio',
            # Resilience metrics
            'mitigation_effective',
            'cost_premium',
            'route_segment',
            # Entity IDs
            'assessment_id',
        ]


# Example usage
if __name__ == "__main__":
    from settings import DATA_DIR
    
    df_cleaned = pd.read_csv(os.path.join(DATA_DIR, "data_cleaned.csv"))
    print(f"Loaded {len(df_cleaned)} rows from data_cleaned.csv")

    transformer = DataTransformer(df_cleaned)
    df_transformed, stats = transformer.transform()
    transformer.save_output()

    print("\n" + "="*60)
    print("NEW COLUMNS ADDED")
    print("="*60)
    for col in transformer.get_new_columns():
        print(f"   - {col}")