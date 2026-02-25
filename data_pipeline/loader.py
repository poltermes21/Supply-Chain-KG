"""
Data Loader Module

Handles loading the supply chain CSV file.
"""

import pandas as pd
import os
from settings import DATA_DIR, DATA_FILENAME


class DataLoader:
    """Load CSV data for the supply chain knowledge graph."""
    
    def __init__(self, data_dir: str = None, filename: str = None):
        """
        Initialize the DataLoader.
        
        Args:
            data_dir: Directory containing the CSV file (default from settings)
            filename: Name of the CSV file (default from settings)
        """
        self.data_dir = data_dir if data_dir is not None else DATA_DIR
        self.filename = filename if filename is not None else DATA_FILENAME
        self.filepath = os.path.join(self.data_dir, self.filename)
        
    def load(self) -> pd.DataFrame:
        """
        Load the CSV file into a pandas DataFrame.
        
        Note: Data exploration confirmed no missing values, duplicates, or outliers.
              No additional cleaning is required.
        
        Returns:
            DataFrame containing the CSV data
        """
        df = pd.read_csv(self.filepath)
        return df


if __name__ == "__main__":
    loader = DataLoader()
    df = loader.load()
    print(f"Loaded {len(df)} rows from {loader.filepath}")