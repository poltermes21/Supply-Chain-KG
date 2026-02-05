"""
Data Loader Module

Handles loading the supply chain CSV file and basic data cleaning operations.
"""

import pandas as pd
from typing import DataFrame
import os

class DataLoader():
    """Load and clean CSV data for the suppy chain knowledge graph"""
    
    def __init__(self, data_dir: str = "data", filename: str = "dynamic_supply_chain_logistics_dataset_with_country.csv"):
        """
        Initialize the DataLoader
        
        Args:
            data_dir: Directory containing the CSV file
            filename: Name of the CSV file
        """
        
        self.data_dir = data_dir
        self.filename = filename
        self.filepath = os.path.join(data_dir, filename)
        
    def load(self):
        """
        Load the CSV file into a pandas Dataframe
        
        Note: Data exploration confirmed no missing values, duplicates, or outliers.
              No additional cleaning is required.
        
        Returns:
            df: Dataframe containing the CSV data
        """
        
        df = pd.read_csv(self.filepath)
        return df
        
        
        
        
        