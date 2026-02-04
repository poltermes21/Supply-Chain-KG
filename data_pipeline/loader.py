"""
Data Loader Module

Handles loading CSV files and basic data cleaning operations.
"""

import pandas as pd
from typing import Dict, List, Optional
import os


class DataLoader:
    """Load and clean CSV data for the supply chain knowledge graph."""
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the DataLoader.
        
        Args:
            data_dir: Directory containing CSV files
        """
        self.data_dir = data_dir
        
    def load_csv(self, filename: str, **kwargs) -> pd.DataFrame:
        """
        Load a CSV file into a pandas DataFrame.
        
        Args:
            filename: Name of the CSV file
            **kwargs: Additional arguments to pass to pd.read_csv
            
        Returns:
            DataFrame containing the CSV data
        """
        filepath = os.path.join(self.data_dir, filename)
        df = pd.read_csv(filepath, **kwargs)
        return df
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean the DataFrame by handling missing values and duplicates.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Remove rows with all NaN values
        df = df.dropna(how='all')
        
        # Strip whitespace from string columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip() if df[col].dtype == 'object' else df[col]
        
        return df
    
    def load_all_data(self) -> Dict[str, pd.DataFrame]:
        """
        Load all CSV files from the data directory.
        
        Returns:
            Dictionary mapping file names (without extension) to DataFrames
        """
        data = {}
        
        if not os.path.exists(self.data_dir):
            return data
            
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.csv'):
                name = filename[:-4]  # Remove .csv extension
                try:
                    df = self.load_csv(filename)
                    df = self.clean_data(df)
                    data[name] = df
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
                    
        return data
