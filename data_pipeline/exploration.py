"""
Data Exploration Module

Performs exploratory data analysis: dimensions, types, missing values,
duplicates, distributions, and outliers.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict


class DataExplorer:
    """
    Exploratory Data Analysis for supply chain dataset.
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize the DataExplorer.
        
        Args:
            df: Dataframe to explore
        """
        self.df = df
        self.stats = {}
    
    def basic_info(self):
        """Display basic dataset information."""
        print("="*60)
        print("BASIC DATASET INFORMATION")
        print("="*60)
        print(f"Rows: {self.df.shape[0]}")
        print(f"Columns: {self.df.shape[1]}")
        print(f"\nColumn names:\n{list(self.df.columns)}")
        print(f"\nData types:\n{self.df.dtypes}")
        
        self.stats['rows'] = self.df.shape[0]
        self.stats['columns'] = self.df.shape[1]
    
    def check_missing_values(self):
        """Check for missing values."""
        print("\n" + "="*60)
        print("MISSING VALUES")
        print("="*60)
        missing = self.df.isnull().sum()
        if missing.sum() == 0:
            print("No missing values found")
        else:
            print(missing[missing > 0])
        
        self.stats['missing_values'] = missing.sum()
    
    def check_duplicates(self):
        """Check for duplicate rows."""
        print("\n" + "="*60)
        print("DUPLICATES")
        print("="*60)
        duplicates = self.df.duplicated().sum()
        if duplicates == 0:
            print("No duplicate rows found")
        else:
            print(f"Found {duplicates} duplicate rows")
        
        self.stats['duplicates'] = duplicates
    
    def describe_numerical(self):
        """Statistical description of numerical columns."""
        print("\n" + "="*60)
        print("NUMERICAL COLUMNS STATISTICS")
        print("="*60)
        print(self.df.describe())
    
    def describe_categorical(self):
        """Distribution of categorical columns."""
        print("\n" + "="*60)
        print("CATEGORICAL COLUMNS DISTRIBUTION")
        print("="*60)
        cat_cols = self.df.select_dtypes(include=['object']).columns
        for col in cat_cols:
            print(f"\n{col}: {self.df[col].nunique()} unique values")
            print(self.df[col].value_counts().head(10))
    
    def check_ranges(self):
        """Check min/max for float columns."""
        print("\n" + "="*60)
        print("VALUE RANGES (float columns)")
        print("="*60)
        float_columns = self.df.select_dtypes(include=['float64']).columns
        for col in float_columns:
            min_val = self.df[col].min()
            max_val = self.df[col].max()
            print(f"{col}: min={min_val:.4f}, max={max_val:.4f}")
    
    def detect_outliers(self):
        """Detect outliers using z-score."""
        print("\n" + "="*60)
        print("OUTLIERS (z-score > 3)")
        print("="*60)
        float_columns = self.df.select_dtypes(include=['float64']).columns
        outlier_report = {}
        for col in float_columns:
            z_scores = (self.df[col] - self.df[col].mean()) / self.df[col].std()
            outliers = self.df[(z_scores > 3) | (z_scores < -3)]
            outlier_report[col] = len(outliers)
        
        if sum(outlier_report.values()) == 0:
            print("No outliers detected (z-score threshold = 3)")
        else:
            for col, count in outlier_report.items():
                if count > 0:
                    print(f"  {col}: {count} outliers")
        
        self.stats['outliers'] = outlier_report
    
    def explore(self) -> Dict:
        """
        Run complete exploration pipeline.
        
        Returns:
            Dictionary with exploration statistics
        """
        self.basic_info()
        self.check_missing_values()
        self.check_duplicates()
        self.describe_numerical()
        self.describe_categorical()
        self.check_ranges()
        self.detect_outliers()
        
        print("\n" + "="*60)
        print("EXPLORATION COMPLETE")
        print("="*60)
        
        return self.stats


# Example usage
if __name__ == "__main__":
    from loader import DataLoader
    
    # Load data
    loader = DataLoader()
    df = loader.load_csv()
    
    # Explore data
    explorer = DataExplorer(df)
    stats = explorer.explore()