"""
Data Exploration Module

Performs exploratory data analysis: dimensions, types, missing values,
duplicates, distributions, and outliers.
"""

import pandas as pd
import warnings
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
    
    def analyze_dates(self):
        """Analyze date columns if present."""
        date_cols = list(self.df.select_dtypes(include=['datetime64']).columns)
        # Also check object columns that look like dates
        for col in self.df.select_dtypes(include=['object']).columns:
            sample = self.df[col].dropna().head(5)
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    parsed = pd.to_datetime(sample, format='%Y-%m-%d')
                date_cols.append(col)
            except (ValueError, TypeError):
                pass

        if len(date_cols) == 0:
            return

        print("\n" + "="*60)
        print("DATE COLUMNS ANALYSIS")
        print("="*60)
        for col in date_cols:
            dates = pd.to_datetime(self.df[col], format='%Y-%m-%d', errors='coerce')
            valid = dates.notna().sum()
            print(f"\n{col}:")
            print(f"  Valid dates: {valid}/{len(self.df)}")
            if valid > 0:
                print(f"  Range: {dates.min()} -> {dates.max()}")
                print(f"  Span: {(dates.max() - dates.min()).days} days")

    def check_ranges(self):
        """Check min/max for numeric columns."""
        print("\n" + "="*60)
        print("VALUE RANGES (numeric columns)")
        print("="*60)
        num_columns = self.df.select_dtypes(include=['number']).columns
        for col in num_columns:
            min_val = self.df[col].min()
            max_val = self.df[col].max()
            print(f"{col}: min={min_val}, max={max_val}")
    
    def detect_outliers(self):
        """Detect outliers using z-score."""
        print("\n" + "="*60)
        print("OUTLIERS (z-score > 3)")
        print("="*60)
        num_columns = self.df.select_dtypes(include=['number']).columns
        outlier_report = {}
        for col in num_columns:
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
        self.analyze_dates()
        self.check_ranges()
        self.detect_outliers()
        
        print("\n" + "="*60)
        print("EXPLORATION COMPLETE")
        print("="*60)
        
        return self.stats


# Example usage
if __name__ == "__main__":
    from .loader import DataLoader

    # Load data
    loader = DataLoader()
    df = loader.load()

    # Explore data
    explorer = DataExplorer(df)
    stats = explorer.explore()