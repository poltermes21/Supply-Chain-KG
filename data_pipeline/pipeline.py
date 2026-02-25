"""
Data Pipeline Orchestrator - Supply Chain Resilience Dataset

Runs the full data pipeline in sequence:
    1. Load    → DataLoader    reads the raw CSV
    2. Clean   → DataCleaner   validates, normalizes and flags inconsistencies
    3. Transform → DataTransformer  creates derived fields and KG-ready columns
"""

import json
import time
from settings import DATA_DIR, DATA_FILENAME

from .loader import DataLoader
from .cleaner import DataCleaner
from .transformer import DataTransformer


def run_pipeline(
    data_dir: str = None,
    filename: str = None,
    save_intermediate: bool = True,
    verbose: bool = True
) -> dict:
    """
    Execute the complete data pipeline: Load → Clean → Transform.

    Args:
        data_dir:          Directory containing the raw CSV (default from settings)
        filename:          Raw CSV filename (default from settings)
        save_intermediate: If True, saves cleaned and transformed CSVs to disk
        verbose:           If True, prints step summaries

    Returns:
        Dictionary with pipeline results:
        {
            'df_cleaned':            cleaned DataFrame,
            'df_transformed':        transformed DataFrame,
            'cleaning_report':       dict with cleaning stats,
            'transformation_stats':  dict with transformation stats,
            'duration_seconds':      total pipeline runtime
        }
    """
    pipeline_start = time.time()

    # 1. LOAD
    _print_header("STEP 1: LOAD", verbose)

    loader = DataLoader(
        data_dir=data_dir or DATA_DIR,
        filename=filename or DATA_FILENAME
    )
    df_raw = loader.load()

    if verbose:
        print(f"   Loaded {len(df_raw)} rows, {len(df_raw.columns)} columns")
        print(f"   Source: {loader.filepath}")

    # 2. CLEAN
    _print_header("STEP 2: CLEAN", verbose)

    cleaner = DataCleaner(df_raw)
    df_cleaned, cleaning_report = cleaner.clean()

    if save_intermediate:
        cleaner.save_outputs(output_dir=DATA_DIR)

    if verbose:
        flagged = cleaning_report['records_with_issues']
        total = cleaning_report['total_records']
        print(f"\n   Records flagged: {flagged}/{total} ({flagged/total*100:.2f}%)")
        print(f"   Inconsistencies: {json.dumps(cleaning_report['inconsistencies'], indent=6)}")

    # 3. TRANSFORM
    _print_header("STEP 3: TRANSFORM", verbose)

    transformer = DataTransformer(df_cleaned)
    df_transformed, transformation_stats = transformer.transform()

    if save_intermediate:
        transformer.save_output(output_dir=DATA_DIR)

    if verbose:
        added = transformation_stats['columns']['added']
        final = transformation_stats['columns']['final']
        print(f"\n   Columns added: {added} (total: {final})")
        print(f"   New columns: {transformer.get_new_columns()}")

    # SUMMARY
    duration = round(time.time() - pipeline_start, 2)
    _print_header("PIPELINE COMPLETE", verbose)

    if verbose:
        print(f"   Duration:           {duration}s")
        print(f"   Raw rows:           {len(df_raw)}")
        print(f"   Final columns:      {len(df_transformed.columns)}")
        print(f"   Flagged records:    {cleaning_report['records_with_issues']}")
        print(f"   Derived fields:     {transformation_stats['columns']['added']}")
        if save_intermediate:
            print(f"   Outputs saved to:   {DATA_DIR}/")

    return {
        'df_cleaned': df_cleaned,
        'df_transformed': df_transformed,
        'cleaning_report': cleaning_report,
        'transformation_stats': transformation_stats,
        'duration_seconds': duration
    }


def _print_header(title: str, verbose: bool):
    """Print a section header if verbose mode is enabled."""
    if verbose:
        print("\n" + "=" * 60)
        print(title)
        print("=" * 60)


if __name__ == "__main__":
    results = run_pipeline(save_intermediate=True, verbose=True)