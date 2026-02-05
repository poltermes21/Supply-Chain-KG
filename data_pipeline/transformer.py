"""
Data Transformation Module

Creates derived fields, composite metrics, and entity identifiers.
Transforms the validated dataset into an enriched version ready for entity extraction.
"""

import pandas as pd
import numpy as np
import os
from typing import Dict
from config import ThresholdConfig


class DataTransformer:
    """
    Transform validated data by creating derived fields and metrics.
    Does NOT validate or clean - assumes input is already validated.
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize the DataTransformer.
        
        Args:
            df: Validated dataframe from DataCleaner
        """
        self.df = df.copy()
        self.config = ThresholdConfig(self.df)
    
    def create_classification_fields(self):
        """
        Create binary and categorical classification fields.
        """
        print("\nCreating classification fields...")
        
        # Get thresholds
        minor_delay = self.config.get('minor_delay')
        significant_delay = self.config.get('significant_delay')
        critical_delay = self.config.get('critical_delay')
        critical_inventory = self.config.get('critical_inventory')
        low_inventory = self.config.get('low_inventory')
        excess_inventory = self.config.get('excess_inventory')
        unreliable_supplier = self.config.get('unreliable_supplier')
        high_probability = self.config.get('high_probability')
        reliable_supplier = self.config.get('reliable_supplier')
        
        # Binary: is_delayed
        self.df['is_delayed'] = self.df['delivery_time_deviation'] > 0
        
        # Binary: is_early
        self.df['is_early'] = self.df['delivery_time_deviation'] < 0
        
        # Categorical: delay_severity (using config thresholds)
        conditions_delay = [
            self.df['delivery_time_deviation'] <= 0,
            self.df['delivery_time_deviation'] <= minor_delay,
            self.df['delivery_time_deviation'] <= significant_delay,
            self.df['delivery_time_deviation'] > significant_delay
        ]
        choices_delay = ['None', 'Minor', 'Major', 'Critical']
        self.df['delay_severity'] = np.select(conditions_delay, choices_delay, default='Unknown')
        
        print(f"   delay_severity thresholds: None<=0, Minor<={minor_delay:.2f}, Major<={significant_delay:.2f}, Critical>{significant_delay:.2f}")
        
        # Categorical: inventory_status (using config thresholds)
        conditions_inv = [
            self.df['warehouse_inventory_level'] < critical_inventory,
            self.df['warehouse_inventory_level'] < low_inventory,
            self.df['warehouse_inventory_level'] < excess_inventory,
            self.df['warehouse_inventory_level'] >= excess_inventory
        ]
        choices_inv = ['Critical', 'Low', 'Normal', 'Excess']
        self.df['inventory_status'] = np.select(conditions_inv, choices_inv, default='Unknown')
        
        print(f"   inventory_status thresholds: Critical<{critical_inventory:.2f}, Low<{low_inventory:.2f}, Normal<{excess_inventory:.2f}, Excess>={excess_inventory:.2f}")
        
        # Categorical: supplier_reliability_category (using config thresholds)
        conditions_rel = [
            self.df['supplier_reliability_score'] < unreliable_supplier,
            self.df['supplier_reliability_score'] < high_probability,
            self.df['supplier_reliability_score'] < reliable_supplier,
            self.df['supplier_reliability_score'] >= reliable_supplier
        ]
        choices_rel = ['Unreliable', 'Average', 'Reliable', 'Excellent']
        self.df['supplier_reliability_category'] = np.select(conditions_rel, choices_rel, default='Unknown')
        
        print(f"   supplier_reliability_category thresholds: Unreliable<{unreliable_supplier}, Average<{high_probability}, Reliable<{reliable_supplier}, Excellent>={reliable_supplier}")
        
        print(f"   Created 6 classification fields")
    
    def create_composite_metrics(self):
        """
        Create composite scores and ratios from multiple variables.
        """
        print("\nCreating composite metrics...")
        
        # delivery_performance_score (0-1)
        self.df['delivery_performance_score'] = (
            self.df['order_fulfillment_status'] * 0.4 +
            (1 - np.minimum(np.abs(self.df['delivery_time_deviation']) / 10, 1)) * 0.3 +
            self.df['cargo_condition_status'] * 0.3
        )
        
        # total_risk_score (0-1)
        self.df['total_risk_score'] = (
            self.df['delay_probability'] * 0.25 +
            self.df['disruption_likelihood_score'] * 0.25 +
            (self.df['route_risk_level'] / 10) * 0.2 +
            self.df['weather_condition_severity'] * 0.15 +
            (1 - self.df['cargo_condition_status']) * 0.15
        )
        
        # cost_efficiency_ratio (cost per day of lead time)
        self.df['cost_efficiency_ratio'] = self.df['shipping_costs'] / self.df['lead_time_days']
        
        # demand_to_inventory_ratio
        # Avoid division by zero
        self.df['demand_to_inventory_ratio'] = np.where(
            self.df['warehouse_inventory_level'] > 0,
            self.df['historical_demand'] / self.df['warehouse_inventory_level'],
            999.0  # High value indicating critical stockout risk
        )
        
        # customs_delay_impact (percentage of lead time spent in customs)
        self.df['customs_delay_impact'] = (
            self.df['customs_clearance_time'] / self.df['lead_time_days']
        ) * 100
        
        # reliability_risk_mismatch (detect misaligned supplier quality vs route risk)
        self.df['reliability_risk_mismatch'] = np.abs(
            self.df['supplier_reliability_score'] - (1 - self.df['total_risk_score'])
        )
        
        print(f"   Created 6 composite metrics")
    
    def create_entity_identifiers(self):
        """
        Create identifier fields for graph entities (nodes and relationships).
        """
        print("\nCreating entity identifiers...")
        
        # route_id: identifies Route nodes
        self.df['route_id'] = self.df['supplier_country'] + '_to_Warehouse'
        
        # risk_assessment_id: identifies RiskAssessment nodes
        self.df['risk_assessment_id'] = (
            self.df['route_id'] + '_' + self.df['risk_classification']
        )
        
        # supplier_product_key: identifies SUPPLIES relationships
        self.df['supplier_product_key'] = (
            self.df['supplier_id'] + '_' + self.df['product_id']
        )
        
        print(f"   Created 3 entity identifiers")
        print(f"      - {self.df['route_id'].nunique()} unique routes")
        print(f"      - {self.df['risk_assessment_id'].nunique()} unique risk assessments")
        print(f"      - {self.df['supplier_product_key'].nunique()} unique supplier-product pairs")
    
    def transform(self) -> pd.DataFrame:
        """
        Execute complete transformation pipeline.
        
        Returns:
            Transformed dataframe with all derived fields
        """
        print("="*60)
        print("STARTING DATA TRANSFORMATION PIPELINE")
        print("="*60)
        
        # Print thresholds being used
        print("\nUsing data-driven thresholds:")
        self.config.print_summary()
        
        original_cols = len(self.df.columns)
        
        # Create all derived fields
        self.create_classification_fields()
        self.create_composite_metrics()
        self.create_entity_identifiers()
        
        new_cols = len(self.df.columns)
        added_cols = new_cols - original_cols
        
        print("\n" + "="*60)
        print("TRANSFORMATION COMPLETE")
        print("="*60)
        print(f"Original columns: {original_cols}")
        print(f"New columns: {new_cols}")
        print(f"Added: {added_cols} derived fields")
        
        return self.df
    
    def save_output(self, output_dir: str = "data", filename: str = "data_transformed.csv"):
        """
        Save transformed dataset.
        
        Args:
            output_dir: Directory to save output
            filename: Output filename
        """
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        self.df.to_csv(output_path, index=False)
        print(f"\nSaved transformed dataset to {output_path}")
        print(f"Total columns: {len(self.df.columns)}")
        print(f"Total rows: {len(self.df)}")


# Example usage
if __name__ == "__main__":
    import pandas as pd
    
    # Load validated data (output from cleaning.py)
    df_validated = pd.read_csv("data/data_validated.csv")
    
    # Transform data
    transformer = DataTransformer(df_validated)
    df_transformed = transformer.transform()
    
    # Save output
    transformer.save_output()