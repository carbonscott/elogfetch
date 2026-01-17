"""Fetch file manager data for an experiment."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .client import ElogClient
from ..exceptions import APIError
from ..utils import get_logger

logger = get_logger()


def fetch_file_manager(
    client: ElogClient,
    experiment_id: str,
) -> dict[str, Any] | None:
    """Fetch file manager data for an experiment.

    This aggregates file data by run number to provide:
    - number_of_files per run
    - total_size_bytes per run

    Args:
        client: ElogClient instance
        experiment_id: The experiment ID to fetch

    Returns:
        Dictionary with file manager data, or None on error
    """
    endpoint = f"/ws-kerb/lgbk/lgbk/{experiment_id}/ws/files"

    try:
        data = client.get(endpoint)

        if not data.get("success"):
            logger.error(f"API returned success=False for files of {experiment_id}")
            return None

        files = data.get("value", [])
        logger.info(f"Fetched {len(files)} files for {experiment_id}")

        # Aggregate by run number
        aggregated = _aggregate_by_run(files)

        return {
            "experiment_id": experiment_id,
            "file_manager_records": aggregated,
        }

    except APIError as e:
        logger.error(f"Failed to fetch file manager for {experiment_id}: {e}")
        return None


def _aggregate_by_run(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate file data by run number.

    Args:
        files: List of file info dictionaries

    Returns:
        List of aggregated records per run
    """
    run_data: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"number_of_files": 0, "total_size_bytes": 0}
    )

    for file_info in files:
        run_num = file_info.get("run_num")
        if run_num is None:
            continue

        size = file_info.get("size", 0) or 0
        run_data[run_num]["number_of_files"] += 1
        run_data[run_num]["total_size_bytes"] += size

    # Convert to list format
    return [
        {
            "run_number": run_num,
            "number_of_files": data["number_of_files"],
            "total_size_bytes": data["total_size_bytes"],
        }
        for run_num, data in sorted(run_data.items())
    ]
