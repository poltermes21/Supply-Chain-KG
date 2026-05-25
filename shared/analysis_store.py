"""
Shared helpers for reading scheduled analysis outputs from Parquet.

The scheduler writes a manifest plus one ``latest.parquet`` per query, so the
Streamlit pages can load cached results without querying Neo4j on each render.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from settings import DATA_DIR, PROJECT_ROOT


def resolve_analysis_root(data_dir: str | Path | None = None) -> Path:
    """Return the absolute analysis output directory."""
    root = Path(data_dir or DATA_DIR)
    if not root.is_absolute():
        root = PROJECT_ROOT / root
    return root / "analysis"


def manifest_path(data_dir: str | Path | None = None) -> Path:
    return resolve_analysis_root(data_dir) / "manifest.parquet"


def load_manifest(data_dir: str | Path | None = None) -> pd.DataFrame:
    path = manifest_path(data_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"Analysis manifest not found at {path}. Run analysis.scheduler first."
        )
    return pd.read_parquet(path)


def load_block_data(
    block_name: str,
    query_names: Iterable[str] | None = None,
    data_dir: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Load the latest parquet for a block as a dict of DataFrames."""
    manifest = load_manifest(data_dir)
    block_rows = manifest[
        (manifest["block"] == block_name)
        & (manifest["status"] == "written")
    ]

    if query_names is not None:
        block_rows = block_rows[block_rows["query_name"].isin(list(query_names))]

    if block_rows.empty:
        raise FileNotFoundError(
            f"No written analysis outputs found for block '{block_name}'."
        )

    analysis_root = resolve_analysis_root(data_dir)
    data: dict[str, pd.DataFrame] = {}
    for _, row in block_rows.iterrows():
        latest_path = Path(row["latest_path"])
        if not latest_path.exists():
            latest_path = Path(row["parquet_path"])
        if not latest_path.exists():
            # Stored paths may be absolute paths from another machine; reconstruct locally.
            latest_path = analysis_root / row["block"] / row["query_name"] / "latest.parquet"
        if not latest_path.exists():
            raise FileNotFoundError(
                f"Missing parquet for {block_name}/{row['query_name']}: {latest_path}"
            )
        data[str(row["query_name"])] = pd.read_parquet(latest_path)

    return data


def load_query_data(
    block_name: str,
    query_name: str,
    data_dir: str | Path | None = None,
) -> pd.DataFrame:
    """Load one query result from the latest cached parquet."""
    return load_block_data(block_name, [query_name], data_dir=data_dir)[query_name]


if __name__ == "__main__":
    result = load_manifest()
    block2 = result[result["block"] == "block2_risk"]
    print(block2.to_string(index=False))
    