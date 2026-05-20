"""
Scheduler module for the analysis layer.

Runs the query packs from the analysis blocks and persists each result as a
Parquet file under data/analysis so the Streamlit app can load cached
outputs without querying Neo4j on every page render.

Block 3 and Block 4 require write steps before their read queries, so the
scheduler executes those prerequisites first.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from analysis.queriesv2 import (
	Block1Queries,
	Block2Queries,
	Block3Queries,
	Block4Queries,
	Block5Queries,
	Block6Queries,
)
from shared.connection import get_neo4j_driver
from settings import DATA_DIR, PROJECT_ROOT


@dataclass(frozen=True)
class QueryResultSpec:
	block: str
	query_name: str
	query_dir: Path
	version_path: Path
	latest_path: Path
	parquet_path: Path
	rows: int
	columns: int
	status: str
	error: str | None = None


def _resolve_data_root() -> Path:
	data_root = Path(DATA_DIR)
	if not data_root.is_absolute():
		data_root = PROJECT_ROOT / data_root
	return data_root


def _analysis_root() -> Path:
	return _resolve_data_root() / "analysis"


def _utc_now_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


def _run_timestamp() -> str:
	return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _write_dataframe(df: pd.DataFrame, target_path: Path) -> None:
	target_path.parent.mkdir(parents=True, exist_ok=True)
	df.to_parquet(target_path, index=False)


def _run_block(
	block_name: str,
	query_results: dict[str, pd.DataFrame],
	output_root: Path,
	timestamp: str,
) -> list[QueryResultSpec]:
	block_dir = output_root / block_name
	block_dir.mkdir(parents=True, exist_ok=True)

	specs: list[QueryResultSpec] = []
	for query_name, df in query_results.items():
		query_dir = block_dir / query_name
		version_path = query_dir / f"{timestamp}.parquet"
		latest_path = query_dir / "latest.parquet"
		_write_dataframe(df, version_path)
		_write_dataframe(df, latest_path)
		specs.append(
			QueryResultSpec(
				block=block_name,
				query_name=query_name,
				query_dir=query_dir,
				version_path=version_path,
				latest_path=latest_path,
				parquet_path=latest_path,
				rows=len(df),
				columns=len(df.columns),
				status="written",
			)
		)

	return specs


def _safe_run_block(
	block_name: str,
	runner: Callable[[], dict[str, pd.DataFrame]],
	output_root: Path,
	timestamp: str,
) -> list[QueryResultSpec]:
	try:
		results = runner()
		return _run_block(block_name, results, output_root, timestamp)
	except Exception as exc:
		return [
			QueryResultSpec(
				block=block_name,
				query_name="__block_error__",
				query_dir=output_root / block_name / "__block_error__",
				version_path=output_root / block_name / "__block_error__" / f"{timestamp}.parquet",
				latest_path=output_root / block_name / "__block_error__" / "latest.parquet",
				parquet_path=output_root / block_name / "__block_error__" / "latest.parquet",
				rows=0,
				columns=0,
				status="failed",
				error=str(exc),
			)
		]


def run_analysis_scheduler(
	driver=None,
	output_root: Path | None = None,
	scenario_config: dict[str, object] | None = None,
) -> pd.DataFrame:
	"""
	Run the scheduled analysis query packs and persist them to Parquet.

	Args:
		driver: Optional Neo4j driver. If omitted, a new one is created.
		output_root: Optional destination root. Defaults to data/analysis.
		scenario_config: Optional parameters for Block 6 what-if queries.

	Returns:
		A manifest DataFrame describing every stored result.
	"""

	analysis_root = Path(output_root) if output_root is not None else _analysis_root()
	analysis_root.mkdir(parents=True, exist_ok=True)

	owns_driver = driver is None
	if driver is None:
		driver = get_neo4j_driver()

	manifest_rows: list[dict[str, object]] = []
	run_timestamp = _utc_now_iso()
	file_stamp = _run_timestamp()

	try:
		# Block 3 and 4 need graph writes before the read-only exports.
		Block3Queries.write_all(driver)
		Block4Queries.write_all(driver)

		block_specs: list[tuple[str, Callable[[], dict[str, pd.DataFrame]]]] = [
			("block1_operational", lambda: Block1Queries.run_all(driver)),
			("block2_risk", lambda: Block2Queries.run_risk_pack(driver)),
			("block3_vulnerability", lambda: Block3Queries.run_all(driver)),
			("block4_geography", lambda: Block4Queries.run_all(driver)),
			("block5_costs", lambda: Block5Queries.run_all(driver)),
		]

		if scenario_config:
			block_specs.append(
				(
					"block6_what_if",
					lambda: Block6Queries.run_scenario_pack(driver, **scenario_config),
				)
			)

		for block_name, runner in block_specs:
			for spec in _safe_run_block(block_name, runner, analysis_root, file_stamp):
				manifest_rows.append(
					{
						**asdict(spec),
						"generated_at_utc": run_timestamp,
						"output_root": str(analysis_root),
						"version_stamp": file_stamp,
					}
				)

		# Ensure any Path objects are converted to strings so pyarrow can serialize
		for row in manifest_rows:
			for k, v in list(row.items()):
				if isinstance(v, Path):
					row[k] = str(v)
		manifest = pd.DataFrame(manifest_rows)
		manifest_path = analysis_root / "manifest.parquet"
		_write_dataframe(manifest, manifest_path)
		return manifest
	finally:
		if owns_driver:
			driver.close()


def main() -> None:
	manifest = run_analysis_scheduler()
	print(manifest[["block", "query_name", "status", "parquet_path"]].to_string(index=False))


if __name__ == "__main__":
	main()
