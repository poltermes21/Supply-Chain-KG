"""
Configuration Module

Defines thresholds for data validation and transformation.
All thresholds are data-driven, based on statistical distributions.
"""

import pandas as pd
from typing import Dict


class ThresholdConfig:
    """
    Calculate and store data-driven thresholds for validation and transformation.
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize thresholds based on dataset distribution.
        
        Args:
            df: Raw dataframe (before cleaning)
        """
        self.df = df
        self.thresholds = {}
        self._calculate_all()
    
    def _calculate_all(self):
        """Calculate all thresholds from data distribution."""
        
        # ============================================================
        # DELAY THRESHOLDS
        # ============================================================
        
        # Significant delay: values above 75th percentile
        self.thresholds['significant_delay'] = self.df['delivery_time_deviation'].quantile(0.75)
        
        # Minor delay: between median and 75th percentile
        self.thresholds['minor_delay'] = self.df['delivery_time_deviation'].quantile(0.50)
        
        # Critical delay: above 90th percentile
        self.thresholds['critical_delay'] = self.df['delivery_time_deviation'].quantile(0.90)
        
        # ============================================================
        # DEMAND THRESHOLDS
        # ============================================================
        
        # High demand: top 25% of observed demand
        self.thresholds['high_demand'] = self.df['historical_demand'].quantile(0.75)
        
        # Low demand: bottom 25%
        self.thresholds['low_demand'] = self.df['historical_demand'].quantile(0.25)
        
        # ============================================================
        # INVENTORY THRESHOLDS
        # ============================================================
        
        # Critical inventory: below 10th percentile
        self.thresholds['critical_inventory'] = self.df['warehouse_inventory_level'].quantile(0.10)
        
        # Low inventory: below 25th percentile
        self.thresholds['low_inventory'] = self.df['warehouse_inventory_level'].quantile(0.25)
        
        # Excess inventory: above 90th percentile
        self.thresholds['excess_inventory'] = self.df['warehouse_inventory_level'].quantile(0.90)
        
        # ============================================================
        # PROBABILITY THRESHOLDS (for [0,1] variables)
        # ============================================================
        # These use domain knowledge: fractions of the [0,1] range
        
        self.thresholds['high_probability'] = 0.7   # 70% is conventionally "high"
        self.thresholds['low_probability'] = 0.3    # 30% is conventionally "low"
        self.thresholds['very_high_probability'] = 0.85
        
        # ============================================================
        # RELIABILITY THRESHOLDS
        # ============================================================
        
        self.thresholds['unreliable_supplier'] = 0.5   # Below 50% is poor
        self.thresholds['reliable_supplier'] = 0.85    # Above 85% is excellent
        
        # ============================================================
        # LEAD TIME THRESHOLDS (by geographic distance)
        # ============================================================
        
        # Calculate lead time percentiles by country groups
        nearby_countries = ['France', 'Germany', 'Netherlands', 'Belgium', 'Spain', 'Italy']
        distant_countries = ['Australia', 'New Zealand', 'Argentina', 'South Africa', 'Chile']
        
        nearby_leadtimes = self.df[self.df['supplier_country'].isin(nearby_countries)]['lead_time_days']
        distant_leadtimes = self.df[self.df['supplier_country'].isin(distant_countries)]['lead_time_days']
        
        # Max reasonable lead time for nearby countries: 75th percentile
        self.thresholds['nearby_max_leadtime'] = nearby_leadtimes.quantile(0.75) if len(nearby_leadtimes) > 0 else 10
        
        # Min reasonable lead time for distant countries: 25th percentile
        self.thresholds['distant_min_leadtime'] = distant_leadtimes.quantile(0.25) if len(distant_leadtimes) > 0 else 7
        
        # ============================================================
        # COST THRESHOLDS
        # ============================================================
        
        # High shipping cost: above 90th percentile
        self.thresholds['high_shipping_cost'] = self.df['shipping_costs'].quantile(0.90)
        
        # Low shipping cost: below 10th percentile
        self.thresholds['low_shipping_cost'] = self.df['shipping_costs'].quantile(0.10)
    
    def get(self, key: str) -> float:
        """Get a threshold value by key."""
        return self.thresholds.get(key)
    
    def get_all(self) -> Dict[str, float]:
        """Get all thresholds as dictionary."""
        return self.thresholds.copy()
    
    def print_summary(self):
        """Print all calculated thresholds with explanations."""
        print("\n" + "="*60)
        print("CALCULATED THRESHOLDS (data-driven)")
        print("="*60)
        
        print("\nINVENTORY:")
        print(f"  Critical:  < {self.thresholds['critical_inventory']:.1f} (10th percentile)")
        print(f"  Low:       < {self.thresholds['low_inventory']:.1f} (25th percentile)")
        print(f"  Excess:    > {self.thresholds['excess_inventory']:.1f} (90th percentile)")
        
        print("\nDEMAND:")
        print(f"  Low:       < {self.thresholds['low_demand']:.1f} (25th percentile)")
        print(f"  High:      > {self.thresholds['high_demand']:.1f} (75th percentile)")
        
        print("\nDELAYS:")
        print(f"  Minor:     > {self.thresholds['minor_delay']:.1f} days (50th percentile)")
        print(f"  Significant: > {self.thresholds['significant_delay']:.1f} days (75th percentile)")
        print(f"  Critical:  > {self.thresholds['critical_delay']:.1f} days (90th percentile)")
        
        print("\nLEAD TIME:")
        print(f"  Nearby (max):   {self.thresholds['nearby_max_leadtime']:.1f} days")
        print(f"  Distant (min):  {self.thresholds['distant_min_leadtime']:.1f} days")
        
        print("\nSHIPPING COSTS:")
        print(f"  Low:       < {self.thresholds['low_shipping_cost']:.2f} (10th percentile)")
        print(f"  High:      > {self.thresholds['high_shipping_cost']:.2f} (90th percentile)")
        
        print("\nPROBABILITIES (domain-based):")
        print(f"  Low:       < {self.thresholds['low_probability']}")
        print(f"  High:      > {self.thresholds['high_probability']}")
        print(f"  Very high: > {self.thresholds['very_high_probability']}")


# Example usage
if __name__ == "__main__":
    from loader import DataLoader
    
    loader = DataLoader()
    df = loader.load_csv()
    
    config = ThresholdConfig(df)
    config.print_summary()