"""Fetch run table data for an experiment."""

from __future__ import annotations

from typing import Any

from .client import ElogClient
from ..exceptions import APIError
from ..utils import get_logger

logger = get_logger()

# Prefix for detector parameters in run data
DETECTOR_PREFIX = "DAQ Detectors/"


def fetch_runtable(
    client: ElogClient,
    experiment_id: str,
) -> dict[str, Any] | None:
    """Fetch run table data for an experiment.

    Args:
        client: ElogClient instance
        experiment_id: The experiment ID to fetch

    Returns:
        Dictionary with run data and detector info, or None on error
    """
    base_endpoint = f"/ws-kerb/lgbk/lgbk/{experiment_id}/ws"

    try:
        # Fetch runs list
        runs_data = client.get(f"{base_endpoint}/runs", params={"includeParams": "false"})
        if not runs_data.get("value"):
            logger.warning(f"No runs found for {experiment_id}")
            return None

        runs = runs_data["value"]
        logger.info(f"Found {len(runs)} runs for {experiment_id}")

        # Collect all detector keys first
        all_detector_keys = set()
        run_details = {}

        for run in runs:
            run_num = run["num"]
            try:
                detail = client.get(
                    f"{base_endpoint}/runs/{run_num}",
                    params={"includeParams": "true"},
                )
                run_details[run_num] = detail.get("value", {})
                params = run_details[run_num].get("params", {})

                for key in params.keys():
                    if key.startswith(DETECTOR_PREFIX):
                        all_detector_keys.add(key)

            except APIError as e:
                logger.warning(f"Failed to fetch run {run_num} details: {e}")

        # Build result structure
        result = {
            "experiment_id": experiment_id,
            "data_production": [],
            "detectors": [],
        }

        for run in runs:
            run_num = run["num"]
            if run_num not in run_details:
                continue

            detail = run_details[run_num]
            params = detail.get("params", {})

            # Data production entry
            result["data_production"].append({
                "run_number": run_num,
                "n_events": params.get("DAQ Detector Totals/Events"),
                "n_damaged": params.get("DAQ Detector Totals/Damaged"),
                "n_dropped": params.get("N dropped Shots"),
                "start_time": _format_time(detail.get("begin_time")),
                "end_time": _format_time(detail.get("end_time")),
                "prod_start": params.get("Prod_start"),
                "prod_end": params.get("Prod_end"),
            })

            # Detector entry
            detector_entry = {"run_number": run_num}
            for key in all_detector_keys:
                detector_entry[key] = "Checked" if params.get(key) else "Unchecked"
            result["detectors"].append(detector_entry)

        logger.info(f"Processed {len(result['data_production'])} runs for {experiment_id}")
        return result

    except APIError as e:
        logger.error(f"Failed to fetch runtable for {experiment_id}: {e}")
        return None


def _format_time(time_str: str | None) -> str | None:
    """Format ISO time string for display."""
    if not time_str:
        return None
    return time_str.replace("T", " ").split("+")[0]
