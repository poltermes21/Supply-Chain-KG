"""
Data Cleaning Module

Validates data quality, detects semantic inconsistencies, and normalizes values.
Outputs: validated dataset with flags + cleaning report.
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, Tuple
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class DataCleaner:
    """
    Validates and cleans supply chain resilience data.
    Focuses on quality assurance and normalization.
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
        self.cleaning_actions = []
        
    # =========================================================================
    # 1. FILL MISSING VALUES
    # =========================================================================
    
    def fill_disruption_events(self):
        """
        Fill missing Disruption_Event values with 'No_Disruption'.
        
        Rationale: NaN means no disruption occurred, not missing data.
        """
        print("Filling missing Disruption_Event...")
        
        missing_count = self.df['Disruption_Event'].isna().sum()
        self.df['Disruption_Event'] = self.df['Disruption_Event'].fillna('No_Disruption')
        
        self.cleaning_actions.append({
            'action': 'fill_disruption_events',
            'records_affected': int(missing_count),
            'fill_value': 'No_Disruption'
        })
        
        print(f"   Filled {missing_count} records with 'No_Disruption'")
        return missing_count
    
    # =========================================================================
    # 2. CONVERT DATA TYPES
    # =========================================================================
    
    def convert_order_date(self):
        """
        Convert Order_Date from string to datetime.
        """
        print("\nConverting Order_Date to datetime...")
        
        original_dtype = str(self.df['Order_Date'].dtype)
        self.df['Order_Date'] = pd.to_datetime(self.df['Order_Date'], format='%Y-%m-%d')
        
        invalid_dates = self.df['Order_Date'].isna().sum()
        
        self.cleaning_actions.append({
            'action': 'convert_order_date',
            'original_dtype': original_dtype,
            'new_dtype': 'datetime64[ns]',
            'invalid_dates': int(invalid_dates)
        })
        
        print(f"   Converted to datetime (invalid dates: {invalid_dates})")
        return invalid_dates
    
    # =========================================================================
    # 3. NORMALIZE LOCATION DATA (Separate City and Country)
    # =========================================================================
    
    def normalize_locations(self):
        """
        Split Origin_City and Destination_City into separate city and country columns.
        
        Format: "City, CC" -> city="City", country_code="CC"
        Also maps country codes to full names for the Knowledge Graph.
        """
        print("\nNormalizing location data...")
        
        country_code_map = {
            'IN': 'India',
            'CN': 'China',
            'DE': 'Germany',
            'JP': 'Japan',
            'BR': 'Brazil',
            'UK': 'United Kingdom',
            'NL': 'Netherlands',
            'US': 'United States',
            'SG': 'Singapore'
        }
        
        def split_location(location_str):
            """Split 'City, CC' into (city, country_code, country_name)."""
            if pd.isna(location_str):
                return None, None, None
            parts = location_str.split(', ')
            if len(parts) == 2:
                city, code = parts
                country = country_code_map.get(code, code)
                return city, code, country
            return location_str, None, None
        
        # Process Origin
        origin_split = self.df['Origin_City'].apply(split_location)
        self.df['Origin_City_Name'] = origin_split.apply(lambda x: x[0])
        self.df['Origin_Country_Code'] = origin_split.apply(lambda x: x[1])
        self.df['Origin_Country'] = origin_split.apply(lambda x: x[2])
        
        # Process Destination
        dest_split = self.df['Destination_City'].apply(split_location)
        self.df['Destination_City_Name'] = dest_split.apply(lambda x: x[0])
        self.df['Destination_Country_Code'] = dest_split.apply(lambda x: x[1])
        self.df['Destination_Country'] = dest_split.apply(lambda x: x[2])
        
        # Stats
        unique_origins = self.df['Origin_City_Name'].nunique()
        unique_destinations = self.df['Destination_City_Name'].nunique()
        unique_countries = pd.concat([
            self.df['Origin_Country'], 
            self.df['Destination_Country']
        ]).nunique()
        
        self.normalization_stats['unique_origin_cities'] = unique_origins
        self.normalization_stats['unique_destination_cities'] = unique_destinations
        self.normalization_stats['unique_countries'] = unique_countries
        
        self.cleaning_actions.append({
            'action': 'normalize_locations',
            'new_columns': [
                'Origin_City_Name', 'Origin_Country_Code', 'Origin_Country',
                'Destination_City_Name', 'Destination_Country_Code', 'Destination_Country'
            ]
        })
        
        print(f"   Created separate city/country columns")
        print(f"   Unique origins: {unique_origins}, destinations: {unique_destinations}")
        print(f"   Total unique countries: {unique_countries}")
    
    # =========================================================================
    # 4. DETECT INCONSISTENCIES
    # =========================================================================
    
    def validate_lead_time_logic(self):
        """
        Validate lead time business logic.
        
        Business rules:
        - Scheduled_Lead_Time >= Base_Lead_Time (includes safety buffer)
        - Actual_Lead_Time varies based on real conditions
        - Delay_Days > 0 only when Late
        
        Note: Actual != Base + Delay is NOT an error - it reflects 
        real-world variability (efficiency gains, minor delays absorbed, etc.)
        """
        print("\nValidating lead time logic...")
        
        # Check: Scheduled should always be >= Base
        invalid_scheduled = self.df[
            self.df['Scheduled_Lead_Time_Days'] < self.df['Base_Lead_Time_Days']
        ]
        self.inconsistencies['scheduled_less_than_base'] = len(invalid_scheduled)
        
        # Check: Actual should be positive
        invalid_actual = self.df[self.df['Actual_Lead_Time_Days'] <= 0]
        self.inconsistencies['invalid_actual_lead_time'] = len(invalid_actual)
        
        total = len(invalid_scheduled) + len(invalid_actual)
        if total > 0:
            print(f"   Found {total} lead time logic errors")
        else:
            print(f"   All lead time values valid")
        
        return total
    
    def detect_delay_status_inconsistencies(self):
        """
        Detect mismatches between Delay_Days and Delivery_Status.
        
        Expected:
        - Delay_Days > 0 -> Status = 'Late'
        - Delay_Days == 0 -> Status = 'On Time'
        """
        print("\nDetecting delay/status inconsistencies...")
        
        # Late but no delay
        late_no_delay = self.df[
            (self.df['Delivery_Status'] == 'Late') & 
            (self.df['Delay_Days'] == 0)
        ]
        self.inconsistencies['late_but_no_delay'] = len(late_no_delay)
        
        # On time but with delay
        ontime_with_delay = self.df[
            (self.df['Delivery_Status'] == 'On Time') & 
            (self.df['Delay_Days'] > 0)
        ]
        self.inconsistencies['ontime_but_delayed'] = len(ontime_with_delay)
        
        total = len(late_no_delay) + len(ontime_with_delay)
        if total > 0:
            print(f"   Found {total} delay/status mismatches:")
            if len(late_no_delay) > 0:
                print(f"      - 'Late' with 0 delay: {len(late_no_delay)}")
            if len(ontime_with_delay) > 0:
                print(f"      - 'On Time' with delay > 0: {len(ontime_with_delay)}")
        else:
            print(f"   All delay/status combinations consistent")
        
        return total
    
    def detect_disruption_mitigation_inconsistencies(self):
        """
        Detect mismatches between disruption events and mitigation actions.
        
        Expected:
        - Disruption present -> Mitigation != 'Standard Shipping'
        - No disruption -> Mitigation = 'Standard Shipping'
        """
        print("\nDetecting disruption/mitigation inconsistencies...")
        
        # Disruption but standard shipping (no mitigation taken)
        disruption_no_action = self.df[
            (self.df['Disruption_Event'] != 'No_Disruption') & 
            (self.df['Mitigation_Action_Taken'] == 'Standard Shipping')
        ]
        self.inconsistencies['disruption_no_mitigation'] = len(disruption_no_action)
        
        # No disruption but special mitigation (suspicious)
        no_disruption_special_action = self.df[
            (self.df['Disruption_Event'] == 'No_Disruption') & 
            (self.df['Mitigation_Action_Taken'] != 'Standard Shipping')
        ]
        self.inconsistencies['no_disruption_but_mitigation'] = len(no_disruption_special_action)
        
        total = len(disruption_no_action) + len(no_disruption_special_action)
        if total > 0:
            print(f"   Found {total} disruption/mitigation mismatches:")
            if len(disruption_no_action) > 0:
                print(f"      - Disruption with standard shipping: {len(disruption_no_action)}")
            if len(no_disruption_special_action) > 0:
                print(f"      - No disruption with special action: {len(no_disruption_special_action)}")
        else:
            print(f"   All disruption/mitigation combinations consistent")
        
        return total
    
    def detect_cost_anomalies(self):
        """
        Detect anomalous shipping costs using IQR method.
        """
        print("\nDetecting cost anomalies...")
        
        Q1 = self.df['Shipping_Cost_USD'].quantile(0.25)
        Q3 = self.df['Shipping_Cost_USD'].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        anomalies = self.df[
            (self.df['Shipping_Cost_USD'] < lower_bound) | 
            (self.df['Shipping_Cost_USD'] > upper_bound)
        ]
        
        self.inconsistencies['cost_anomalies'] = len(anomalies)
        self.normalization_stats['cost_bounds'] = {
            'lower': float(lower_bound),
            'upper': float(upper_bound),
            'Q1': float(Q1),
            'Q3': float(Q3)
        }
        
        if len(anomalies) > 0:
            print(f"   Found {len(anomalies)} cost anomalies (IQR method)")
            print(f"   Bounds: ${lower_bound:.2f} - ${upper_bound:.2f}")
        else:
            print(f"   No cost anomalies detected")
        
        return len(anomalies)
    
    def detect_route_location_inconsistencies(self):
        """
        Detect if Route_Type matches origin-destination pairs.
        
        Known mappings based on data:
        - Suez: Europe <-> Asia
        - Atlantic: Europe <-> Americas
        - Pacific: Asia <-> Americas
        - Intra-Asia: Asia <-> Asia
        """
        print("\nDetecting route/location inconsistencies...")
        
        # Define region mappings
        asia_countries = ['India', 'China', 'Japan', 'Singapore']
        europe_countries = ['Germany', 'United Kingdom', 'Netherlands']
        americas_countries = ['United States', 'Brazil']
        
        def get_region(country):
            if country in asia_countries:
                return 'Asia'
            elif country in europe_countries:
                return 'Europe'
            elif country in americas_countries:
                return 'Americas'
            return 'Unknown'
        
        # Add region columns for analysis
        self.df['Origin_Region'] = self.df['Origin_Country'].apply(get_region)
        self.df['Destination_Region'] = self.df['Destination_Country'].apply(get_region)
        
        # Check route consistency
        # Atlantic should be Europe <-> Americas
        atlantic_wrong = self.df[
            (self.df['Route_Type'] == 'Atlantic') &
            ~(
                ((self.df['Origin_Region'] == 'Europe') & (self.df['Destination_Region'] == 'Americas')) |
                ((self.df['Origin_Region'] == 'Americas') & (self.df['Destination_Region'] == 'Europe'))
            )
        ]
        
        # Intra-Asia should be Asia <-> Asia
        intra_asia_wrong = self.df[
            (self.df['Route_Type'] == 'Intra-Asia') &
            ~((self.df['Origin_Region'] == 'Asia') & (self.df['Destination_Region'] == 'Asia'))
        ]
        
        self.inconsistencies['atlantic_route_wrong'] = len(atlantic_wrong)
        self.inconsistencies['intra_asia_route_wrong'] = len(intra_asia_wrong)
        
        total = len(atlantic_wrong) + len(intra_asia_wrong)
        if total > 0:
            print(f"   Found {total} route/location mismatches")
        else:
            print(f"   All routes consistent with locations")
        
        return total
    
    # =========================================================================
    # 5. FLAG PROBLEMATIC RECORDS
    # =========================================================================
    
    def flag_problematic_records(self):
        """
        Add flag columns to dataset for records with inconsistencies.
        """
        print("\nFlagging problematic records...")
        
        self.df['has_inconsistency'] = False
        self.df['inconsistency_flags'] = ''
        
        # Lead time logic errors
        scheduled_base_mask = self.df['Scheduled_Lead_Time_Days'] < self.df['Base_Lead_Time_Days']
        invalid_actual_mask = self.df['Actual_Lead_Time_Days'] <= 0
        
        # Delay/status mismatch
        late_no_delay_mask = (self.df['Delivery_Status'] == 'Late') & (self.df['Delay_Days'] == 0)
        ontime_delay_mask = (self.df['Delivery_Status'] == 'On Time') & (self.df['Delay_Days'] > 0)
        
        # Cost anomalies
        Q1 = self.df['Shipping_Cost_USD'].quantile(0.25)
        Q3 = self.df['Shipping_Cost_USD'].quantile(0.75)
        IQR = Q3 - Q1
        cost_anomaly_mask = (
            (self.df['Shipping_Cost_USD'] < Q1 - 1.5 * IQR) | 
            (self.df['Shipping_Cost_USD'] > Q3 + 1.5 * IQR)
        )
        
        flags_map = {
            'scheduled_less_than_base': scheduled_base_mask,
            'invalid_actual_lead_time': invalid_actual_mask,
            'late_no_delay': late_no_delay_mask,
            'ontime_with_delay': ontime_delay_mask,
            'cost_anomaly': cost_anomaly_mask,
        }
        
        for flag_name, condition in flags_map.items():
            self.df.loc[condition, 'has_inconsistency'] = True
            self.df.loc[condition, 'inconsistency_flags'] = (
                self.df.loc[condition, 'inconsistency_flags'] + flag_name + ';'
            )
        
        self.df['inconsistency_flags'] = self.df['inconsistency_flags'].str.rstrip(';')
        
        flagged_count = self.df['has_inconsistency'].sum()
        print(f"   Flagged {flagged_count} records with inconsistencies")
        
        return flagged_count
    
    # =========================================================================
    # 6. GENERATE REPORT
    # =========================================================================
    
    def generate_cleaning_report(self) -> Dict:
        """
        Generate comprehensive cleaning report.
        """
        report = {
            'total_records': len(self.df),
            'records_with_issues': int(self.df['has_inconsistency'].sum()),
            'cleaning_actions': self.cleaning_actions,
            'inconsistencies': {k: int(v) for k, v in self.inconsistencies.items()},
            'normalization_stats': self.normalization_stats,
            'columns_after_cleaning': list(self.df.columns)
        }
        
        return report
    
    # =========================================================================
    # MAIN PIPELINE
    # =========================================================================
    
    def clean(self) -> Tuple[pd.DataFrame, Dict]:
        """
        Execute complete cleaning pipeline.
        
        Returns:
            Tuple of (cleaned dataframe, cleaning report)
        """
        print("="*60)
        print("STARTING DATA CLEANING PIPELINE")
        print("="*60)
        
        # 1. Fill missing values
        print("\n--- STEP 1: FILL MISSING VALUES ---")
        self.fill_disruption_events()
        
        # 2. Convert data types
        print("\n--- STEP 2: CONVERT DATA TYPES ---")
        self.convert_order_date()
        
        # 3. Normalize locations
        print("\n--- STEP 3: NORMALIZE LOCATIONS ---")
        self.normalize_locations()
        
        # 4. Detect inconsistencies
        print("\n--- STEP 4: DETECT INCONSISTENCIES ---")
        self.validate_lead_time_logic()
        self.detect_delay_status_inconsistencies()
        self.detect_disruption_mitigation_inconsistencies()
        self.detect_cost_anomalies()
        self.detect_route_location_inconsistencies()
        
        # 5. Flag problematic records
        print("\n--- STEP 5: FLAG PROBLEMATIC RECORDS ---")
        self.flag_problematic_records()
        
        # 6. Generate report
        report = self.generate_cleaning_report()
        
        print("\n" + "="*60)
        print("CLEANING COMPLETE")
        print("="*60)
        print(f"Total records: {report['total_records']}")
        print(f"Records flagged: {report['records_with_issues']} ({report['records_with_issues']/report['total_records']*100:.2f}%)")
        print(f"Total inconsistencies detected: {sum(report['inconsistencies'].values())}")
        
        return self.df, report
    
    def save_outputs(self, output_dir: str = "data"):
        """
        Save cleaned dataset and reports.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Save validated dataset
        validated_path = os.path.join(output_dir, "data_cleaned.csv")
        self.df.to_csv(validated_path, index=False)
        print(f"\nSaved cleaned dataset to {validated_path}")
        
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
    
    # Load data
    loader = DataLoader()
    df = loader.load()
    
    # Clean data
    cleaner = DataCleaner(df)
    df_cleaned, report = cleaner.clean()
    
    # Save outputs
    cleaner.save_outputs()
    
    # Print summary
    print("\n" + "="*60)
    print("CLEANING REPORT SUMMARY")
    print("="*60)
    print(json.dumps(report['inconsistencies'], indent=2))
