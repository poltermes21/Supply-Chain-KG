"""
Data Exploration Script

Performs basic exploratory data analysis: shows dataset dimensions, column types, missing values, duplicates, distributions, and outliers.
"""

import pandas as pd

# Load data
supplychainDF = pd.read_csv("data/dynamic_supply_chain_logistics_dataset_with_country.csv")

# Basic dimensions
print(f"Rows: {supplychainDF.shape[0]}, Columns: {supplychainDF.shape[1]}")
print("Columns:", list(supplychainDF.columns))
print("Data types:\n", supplychainDF.dtypes)

# Missing values
print("\nMissing values per column:")
print(supplychainDF.isnull().sum())

# Duplicates
print("\nDuplicate rows (entire row):", supplychainDF.duplicated().sum())

# Distribution of quantitative columns
print("\nStatistical description of numerical columns:")
print(supplychainDF.describe())

# Distribution of categorical columns
cat_cols = supplychainDF.select_dtypes(include=['object']).columns
for col in cat_cols:
    print(f"\n{col}: {supplychainDF[col].nunique()} unique values")
    print(f"{supplychainDF[col].value_counts().head(10)}\n")
    
# Minimum and maximum values for each float column to check for out-of-range values
float_columns = supplychainDF.select_dtypes(include=['float64']).columns
for col in float_columns:
    min_val = supplychainDF[col].min()
    max_val = supplychainDF[col].max()
    print(f"{col}: min = {min_val}, max = {max_val}")
    
# Outliers (z-score > 3 or < -3 for float columns)
float_columns = supplychainDF.select_dtypes(include=['float64']).columns
outlier_report = {}
for col in float_columns:
    z_scores = (supplychainDF[col] - supplychainDF[col].mean()) / supplychainDF[col].std()
    outliers = supplychainDF[(z_scores > 3) | (z_scores < -3)]
    outlier_report[col] = len(outliers)
print("\nOutliers per column (z-score > 3):")
print(outlier_report)