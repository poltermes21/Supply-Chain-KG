"""
Graph Builder Orchestrator - Supply Chain Knowledge Graph

Runs the full KG construction pipeline in sequence:
    1. Extract  → KGExtractor      extracts nodes and relationships from the transformed CSV
    2. Load     → KGLoaderNeo4j    loads nodes and relationships into Neo4j

Inputs:
    - data/data_transformed.csv

Outputs:
    - Neo4j Knowledge Graph (nodes + relationships)
"""

import os
import time
import pandas as pd

from settings import DATA_DIR

from .extractor import KGExtractor
from .loader_neo4j import KGLoaderNeo4j


def run_graph_builder(
    data_dir: str = None,
    filename: str = "data_transformed.csv",
    verbose: bool = True
) -> dict:
    """
    Execute the complete KG construction pipeline: Extract → Load.

    Args:
        data_dir: Directory containing the transformed CSV (default from settings)
        filename: Transformed CSV filename (default: 'data_transformed.csv')
        verbose:  If True, prints step summaries

    Returns:
        Dictionary with pipeline results:
        {
            'kg_data':          dict with nodes and relationships extracted,
            'duration_seconds': total pipeline runtime
        }
    """
    pipeline_start = time.time()

    # 1. EXTRACT
    _print_header("STEP 1: EXTRACT", verbose)

    csv_path = os.path.join(data_dir or DATA_DIR, filename)
    df_transformed = pd.read_csv(csv_path, parse_dates=['Order_Date'])
    print(df_transformed.dtypes)

    if verbose:
        print(f"   Loaded {len(df_transformed)} rows from {csv_path}")

    extractor = KGExtractor(df_transformed)
    kg_data = extractor.extract()

    if verbose:
        total_nodes = sum(len(v) for v in kg_data['nodes'].values())
        total_rels  = sum(len(v) for v in kg_data['relationships'].values())
        print(f"\n   Nodes extracted:         {total_nodes:,}")
        print(f"   Relationships extracted: {total_rels:,}")

    # 2: LOAD
    _print_header("STEP 2: LOAD INTO NEO4J", verbose)

    loader = KGLoaderNeo4j(kg_data)
    loader.load()
    loader.close()

    # SUMMARY
    duration = round(time.time() - pipeline_start, 2)
    _print_header("GRAPH BUILDER COMPLETE", verbose)

    if verbose:
        total_nodes = sum(len(v) for v in kg_data['nodes'].values())
        total_rels  = sum(len(v) for v in kg_data['relationships'].values())
        print(f"   Duration:                {duration}s")
        print(f"   Total nodes loaded:      {total_nodes:,}")
        print(f"   Total relationships:     {total_rels:,}")

    return {
        'kg_data':          kg_data,
        'duration_seconds': duration
    }


def _print_header(title: str, verbose: bool):
    """Print a section header if verbose mode is enabled."""
    if verbose:
        print("\n" + "=" * 60)
        print(title)
        print("=" * 60)


if __name__ == "__main__":
    run_graph_builder(verbose=True)