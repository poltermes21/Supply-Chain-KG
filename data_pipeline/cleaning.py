"""
Data Cleaning Module

Validates data quality, detects semantic inconsistencies, and normalizes values.
Outputs: validated dataset with flags + cleaning report.
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, List, Tuple
import os
from config import ThresholdConfig


class DataCleaner:
    """
    Validates and cleans supply chain data.
    Focuses on quality assurance, not transformation.
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize the DataCleaner.
        
        Args:
            df: Raw dataframe from DataLoader
        """
        self.df = df.copy()
        self.inconsistencies = {}
        self.normalization_stats = {}
        self.out_of_range_count = {}
        
        # Calculate data-driven thresholds
        self.config = ThresholdConfig(self.df)
        
    def validate_ranges(self) -> Dict[str, int]:
        """
        Validate that all variables are within expected ranges.
        
        Returns:
            Dictionary with count of out-of-range values per column
        """
        print("Validating data ranges...")
        
        # Variables with range [0, 1]
        range_0_1_cols = [
            'handling_equipment_availability',
            'order_fulfillment_status',
            'supplier_reliability_score',
            'cargo_condition_status',
            'weather_condition_severity',
            'disruption_likelihood_score',
            'delay_probability'
        ]
        
        for col in range_0_1_cols:
            out_of_range = self.df[(self.df[col] < 0) | (self.df[col] > 1)]
            self.out_of_range_count[col] = len(out_of_range)
            if len(out_of_range) > 0:
                print(f"   {col}: {len(out_of_range)} values out of [0,1] range")
        
        # warehouse_inventory_level: [0, 1000]
        col = 'warehouse_inventory_level'
        out_of_range = self.df[(self.df[col] < 0) | (self.df[col] > 1000)]
        self.out_of_range_count[col] = len(out_of_range)
        if len(out_of_range) > 0:
            print(f"   {col}: {len(out_of_range)} values out of [0,1000] range")
        
        # route_risk_level: [0, 10]
        col = 'route_risk_level'
        out_of_range = self.df[(self.df[col] < 0) | (self.df[col] > 10)]
        self.out_of_range_count[col] = len(out_of_range)
        if len(out_of_range) > 0:
            print(f"   {col}: {len(out_of_range)} values out of [0,10] range")
        
        # Positive values (time, costs, demand)
        positive_cols = [
            'lead_time_days',
            'customs_clearance_time',
            'shipping_costs',
            'historical_demand'
        ]
        
        for col in positive_cols:
            negative = self.df[self.df[col] < 0]
            self.out_of_range_count[col] = len(negative)
            if len(negative) > 0:
                print(f"   {col}: {len(negative)} negative values")
        
        total_issues = sum(self.out_of_range_count.values())
        if total_issues == 0:
            print("   All values within expected ranges")
        
        return self.out_of_range_count
    
    def normalize_countries(self) -> Dict[str, str]:
        """
        Normalize country names to avoid duplicates.
        
        Returns:
            Dictionary mapping original -> normalized names
        """
        print("\nNormalizing country names...")
        
        country_mapping = {
            'USA': 'United States',
            'US': 'United States',
            'U.S.A.': 'United States',
            'UK': 'United Kingdom',
            'U.K.': 'United Kingdom',
            'UAE': 'United Arab Emirates',
            'U.A.E.': 'United Arab Emirates',
        }
        
        original_unique = self.df['supplier_country'].nunique()
        
        # Apply normalization
        self.df['supplier_country'] = self.df['supplier_country'].replace(country_mapping)
        
        normalized_unique = self.df['supplier_country'].nunique()
        unified_count = original_unique - normalized_unique
        
        self.normalization_stats['countries_unified'] = unified_count
        self.normalization_stats['original_countries'] = original_unique
        self.normalization_stats['normalized_countries'] = normalized_unique
        
        if unified_count > 0:
            print(f"   Unified {unified_count} country name(s)")
        else:
            print(f"   No country names needed normalization")
        
        return country_mapping
    
    def normalize_risk_classification(self):
        """
        Normalize risk_classification categories (capitalization, spacing).
        """
        print("\nNormalizing risk classifications...")
        
        # Map variations to standard values
        risk_mapping = {
            'High Risk': 'High',
            'Moderate Risk': 'Moderate',
            'Low Risk': 'Low',
        }
        
        original_unique = self.df['risk_classification'].nunique()
        
        # Apply normalization
        self.df['risk_classification'] = self.df['risk_classification'].replace(risk_mapping)
        
        normalized_unique = self.df['risk_classification'].nunique()
        unified_count = original_unique - normalized_unique
        
        self.normalization_stats['risk_categories_standardized'] = unified_count
        
        if unified_count > 0:
            print(f"   Standardized {unified_count} risk category variation(s)")
        else:
            print(f"   Risk categories already standardized")
    
    def detect_risk_inconsistencies(self):
        """
        Detect inconsistencies between risk_classification and probability metrics.
        """
        print("\nDetecting risk classification inconsistencies...")
        
        high_prob = self.config.get('high_probability')
        low_prob = self.config.get('low_probability')
        
        # Inconsistency 1: Low risk but high probabilities
        low_risk_high_prob = self.df[
            (self.df['risk_classification'] == 'Low') &
            ((self.df['delay_probability'] > high_prob) | (self.df['disruption_likelihood_score'] > high_prob))
        ]
        self.inconsistencies['low_risk_but_high_probability'] = len(low_risk_high_prob)
        
        # Inconsistency 2: High risk but low probabilities
        high_risk_low_prob = self.df[
            (self.df['risk_classification'] == 'High') &
            (self.df['delay_probability'] < low_prob) &
            (self.df['disruption_likelihood_score'] < low_prob)
        ]
        self.inconsistencies['high_risk_but_low_probability'] = len(high_risk_low_prob)
        
        total = len(low_risk_high_prob) + len(high_risk_low_prob)
        if total > 0:
            print(f"   Found {total} risk classification inconsistencies (thresholds: high_prob={high_prob}, low_prob={low_prob})")
        else:
            print(f"   No risk classification inconsistencies")
    
    def detect_delay_inconsistencies(self):
        """
        Detect inconsistencies between actual delays and delay probabilities.
        """
        print("\nDetecting delay inconsistencies...")
        
        high_prob = self.config.get('high_probability')
        low_prob = self.config.get('low_probability')
        significant_delay = self.config.get('significant_delay')
        
        # Inconsistency 3: No delay but high delay probability
        no_delay_high_prob = self.df[
            (self.df['delivery_time_deviation'] <= 0) &
            (self.df['delay_probability'] > high_prob)
        ]
        self.inconsistencies['no_delay_but_high_probability'] = len(no_delay_high_prob)
        
        # Inconsistency 4: Significant delay but low probability
        delay_low_prob = self.df[
            (self.df['delivery_time_deviation'] > significant_delay) &
            (self.df['delay_probability'] < low_prob)
        ]
        self.inconsistencies['significant_delay_but_low_probability'] = len(delay_low_prob)
        
        total = len(no_delay_high_prob) + len(delay_low_prob)
        if total > 0:
            print(f"   Found {total} delay probability inconsistencies (thresholds: significant_delay={significant_delay:.2f}, high_prob={high_prob}, low_prob={low_prob})")
        else:
            print(f"   No delay probability inconsistencies")
    
    def detect_inventory_inconsistencies(self):
        """
        Detect critical inventory situations.
        """
        print("\nDetecting inventory inconsistencies...")
        
        high_demand = self.config.get('high_demand')
        low_demand = self.config.get('low_demand')
        excess_inventory = self.config.get('excess_inventory')
        critical_inventory = self.config.get('critical_inventory')
        
        # Inconsistency 5: Critical/zero inventory with high demand
        zero_inv_high_demand = self.df[
            (self.df['warehouse_inventory_level'] <= critical_inventory) &
            (self.df['historical_demand'] > high_demand)
        ]
        self.inconsistencies['stockout_high_demand'] = len(zero_inv_high_demand)
        
        # Inconsistency 6: Excess inventory with low demand
        excess_inv_low_demand = self.df[
            (self.df['warehouse_inventory_level'] > excess_inventory) &
            (self.df['historical_demand'] < low_demand)
        ]
        self.inconsistencies['excess_inventory_low_demand'] = len(excess_inv_low_demand)
        
        total = len(zero_inv_high_demand) + len(excess_inv_low_demand)
        if total > 0:
            print(f"   Found {total} inventory management issues (thresholds: critical_inv={critical_inventory:.2f}, excess_inv={excess_inventory:.2f}, high_demand={high_demand:.2f}, low_demand={low_demand:.2f})")
            if len(zero_inv_high_demand) > 0:
                print(f"      - {len(zero_inv_high_demand)} CRITICAL stockouts on high-demand products")
        else:
            print(f"   No inventory inconsistencies")
    
    def detect_customs_inconsistencies(self):
        """
        Detect customs time anomalies.
        """
        print("\nDetecting customs inconsistencies...")
        
        # Inconsistency: Customs time > lead time (IMPOSSIBLE)
        customs_exceeds_leadtime = self.df[
            self.df['customs_clearance_time'] > self.df['lead_time_days']
        ]
        self.inconsistencies['customs_exceeds_leadtime'] = len(customs_exceeds_leadtime)
        
        if len(customs_exceeds_leadtime) > 0:
            print(f"   CRITICAL: {len(customs_exceeds_leadtime)} records with customs_time > lead_time")
        else:
            print(f"   No customs time errors")
        
        # Inconsistency: Zero customs in strict countries
        strict_customs_countries = ['China', 'India', 'Brazil', 'Russia', 'Argentina']
        zero_customs_strict = self.df[
            (self.df['supplier_country'].isin(strict_customs_countries)) &
            (self.df['customs_clearance_time'] < 0.5)
        ]
        self.inconsistencies['zero_customs_strict_countries'] = len(zero_customs_strict)
        
        if len(zero_customs_strict) > 0:
            print(f"   {len(zero_customs_strict)} suspiciously fast customs in strict countries")
    
    def detect_geographic_inconsistencies(self):
        """
        Detect lead times inconsistent with geographic distance.
        """
        print("\nDetecting geographic inconsistencies...")
        
        nearby_max = self.config.get('nearby_max_leadtime')
        distant_min = self.config.get('distant_min_leadtime')
        
        # Inconsistency: Too fast for distant countries
        distant_countries = ['Australia', 'New Zealand', 'Argentina', 'South Africa', 'Chile']
        too_fast_distant = self.df[
            (self.df['supplier_country'].isin(distant_countries)) &
            (self.df['lead_time_days'] < distant_min)
        ]
        self.inconsistencies['too_fast_for_distance'] = len(too_fast_distant)
        
        # Inconsistency: Too slow for nearby countries (assuming EU-based warehouse)
        nearby_countries = ['France', 'Germany', 'Netherlands', 'Belgium', 'Spain', 'Italy']
        too_slow_nearby = self.df[
            (self.df['supplier_country'].isin(nearby_countries)) &
            (self.df['lead_time_days'] > nearby_max)
        ]
        self.inconsistencies['too_slow_for_proximity'] = len(too_slow_nearby)
        
        total = len(too_fast_distant) + len(too_slow_nearby)
        if total > 0:
            print(f"   Found {total} geographic inconsistencies (thresholds: nearby_max={nearby_max:.2f} days, distant_min={distant_min:.2f} days)")
        else:
            print(f"   No geographic inconsistencies")
    
    def detect_supplier_inconsistencies(self):
        """
        Detect mismatches between supplier reliability and performance.
        """
        print("\nDetecting supplier performance inconsistencies...")
        
        reliable_threshold = self.config.get('reliable_supplier')
        unreliable_threshold = self.config.get('unreliable_supplier')
        
        # Inconsistency: High reliability but poor fulfillment
        reliable_poor_fulfillment = self.df[
            (self.df['supplier_reliability_score'] > reliable_threshold) &
            (self.df['order_fulfillment_status'] < unreliable_threshold)
        ]
        self.inconsistencies['reliable_supplier_poor_fulfillment'] = len(reliable_poor_fulfillment)
        
        # Inconsistency: Low reliability but excellent performance
        unreliable_good_performance = self.df[
            (self.df['supplier_reliability_score'] < unreliable_threshold) &
            (self.df['order_fulfillment_status'] > reliable_threshold) &
            (self.df['delivery_time_deviation'] <= 0)
        ]
        self.inconsistencies['unreliable_supplier_excellent_performance'] = len(unreliable_good_performance)
        
        total = len(reliable_poor_fulfillment) + len(unreliable_good_performance)
        if total > 0:
            print(f"   Found {total} supplier reliability inconsistencies (thresholds: reliable={reliable_threshold}, unreliable={unreliable_threshold})")
        else:
            print(f"   No supplier reliability inconsistencies")
    
    def flag_problematic_records(self):
        """
        Add flag columns to dataset for records with inconsistencies.
        """
        print("\nFlagging problematic records...")
        
        high_prob = self.config.get('high_probability')
        low_prob = self.config.get('low_probability')
        high_demand = self.config.get('high_demand')
        critical_inventory = self.config.get('critical_inventory')
        
        # Initialize flag columns
        self.df['has_inconsistency'] = False
        self.df['inconsistency_flags'] = ''
        
        # Flag each type of inconsistency
        flags_map = {
            'low_risk_high_prob': (
                (self.df['risk_classification'] == 'Low') &
                ((self.df['delay_probability'] > high_prob) | (self.df['disruption_likelihood_score'] > high_prob))
            ),
            'high_risk_low_prob': (
                (self.df['risk_classification'] == 'High') &
                (self.df['delay_probability'] < low_prob) &
                (self.df['disruption_likelihood_score'] < low_prob)
            ),
            'customs_exceeds_leadtime': (
                self.df['customs_clearance_time'] > self.df['lead_time_days']
            ),
            'stockout_high_demand': (
                (self.df['warehouse_inventory_level'] <= critical_inventory) &
                (self.df['historical_demand'] > high_demand)
            ),
        }
        
        for flag_name, condition in flags_map.items():
            self.df.loc[condition, 'has_inconsistency'] = True
            self.df.loc[condition, 'inconsistency_flags'] = (
                self.df.loc[condition, 'inconsistency_flags'] + flag_name + ';'
            )
        
        # Clean up trailing semicolons
        self.df['inconsistency_flags'] = self.df['inconsistency_flags'].str.rstrip(';')
        
        flagged_count = self.df['has_inconsistency'].sum()
        print(f"   Flagged {flagged_count} records with inconsistencies")
        
        return flagged_count
    
    def generate_cleaning_report(self) -> Dict:
        """
        Generate comprehensive cleaning report.
        
        Returns:
            Dictionary with all cleaning statistics
        """
        report = {
            'total_records': len(self.df),
            'records_with_issues': int(self.df['has_inconsistency'].sum()),
            'out_of_range': self.out_of_range_count,
            'inconsistencies': self.inconsistencies,
            'normalization': self.normalization_stats,
            'thresholds_used': self.config.get_all()
        }
        
        return report
    
    def clean(self) -> Tuple[pd.DataFrame, Dict]:
        """
        Execute complete cleaning pipeline.
        
        Returns:
            Tuple of (cleaned dataframe, cleaning report)
        """
        print("="*60)
        print("STARTING DATA CLEANING PIPELINE")
        print("="*60)
        
        # Print thresholds being used
        print("\nUsing data-driven thresholds:")
        self.config.print_summary()
        
        # 1. Validate ranges
        print("\n")
        self.validate_ranges()
        
        # 2. Normalize values
        self.normalize_countries()
        self.normalize_risk_classification()
        
        # 3. Detect all inconsistencies
        self.detect_risk_inconsistencies()
        self.detect_delay_inconsistencies()
        self.detect_inventory_inconsistencies()
        self.detect_customs_inconsistencies()
        self.detect_geographic_inconsistencies()
        self.detect_supplier_inconsistencies()
        
        # 4. Flag problematic records
        self.flag_problematic_records()
        
        # 5. Generate report
        report = self.generate_cleaning_report()
        
        print("\n" + "="*60)
        print("CLEANING COMPLETE")
        print("="*60)
        print(f"Total records: {report['total_records']}")
        print(f"Records flagged: {report['records_with_issues']} ({report['records_with_issues']/report['total_records']*100:.2f}%)")
        
        return self.df, report
    
    def save_outputs(self, output_dir: str = "data"):
        """
        Save cleaned dataset and reports.
        
        Args:
            output_dir: Directory to save outputs
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Save validated dataset
        validated_path = os.path.join(output_dir, "data_validated.csv")
        self.df.to_csv(validated_path, index=False)
        print(f"\nSaved validated dataset to {validated_path}")
        
        # Save cleaning report
        report = self.generate_cleaning_report()
        report_path = os.path.join(output_dir, "cleaning_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Saved cleaning report to {report_path}")
        
        # Save flagged records only
        flagged = self.df[self.df['has_inconsistency'] == True]
        if len(flagged) > 0:
            flagged_path = os.path.join(output_dir, "flagged_records.csv")
            flagged.to_csv(flagged_path, index=False)
            print(f"Saved {len(flagged)} flagged records to {flagged_path}")


# Example usage
if __name__ == "__main__":
    from loader import DataLoader
    
    # Load data (uses settings defaults)
    loader = DataLoader()
    df = loader.load()
    
    # Clean data
    cleaner = DataCleaner(df)
    df_validated, report = cleaner.clean()
    
    # Save outputs
    cleaner.save_outputs()