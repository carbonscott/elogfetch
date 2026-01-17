"""Fetch logbook entries for an experiment."""

from __future__ import annotations

from typing import Any

from .client import ElogClient
from ..exceptions import APIError
from ..utils import get_logger

logger = get_logger()


def fetch_logbook(
    client: ElogClient,
    experiment_id: str,
) -> list[dict[str, Any]]:
    """Fetch logbook entries for an experiment.

    Args:
        client: ElogClient instance
        experiment_id: The experiment ID to fetch

    Returns:
        List of logbook entries formatted for database
    """
    endpoint = f"/ws-kerb/lgbk/lgbk/{experiment_id}/ws/elog"

    try:
        data = client.get(endpoint)

        if not data.get("success"):
            logger.error(f"API returned success=False for logbook of {experiment_id}")
            return []

        raw_entries = data.get("value", [])
        logger.info(f"Fetched {len(raw_entries)} logbook entries for {experiment_id}")

        return _transform_entries(experiment_id, raw_entries)

    except APIError as e:
        logger.error(f"Failed to fetch logbook for {experiment_id}: {e}")
        return []


def _transform_entries(
    experiment_id: str,
    raw_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Transform logbook entries to database format.

    Args:
        experiment_id: The experiment ID
        raw_entries: Raw entries from the API

    Returns:
        List of transformed entries
    """
    # Sort entries by timestamp
    sorted_entries = sorted(raw_entries, key=lambda x: x.get("insert_time", ""))

    # Identify run boundaries for inference
    run_boundaries = _identify_run_boundaries(sorted_entries)
    inferred_runs = _infer_run_numbers(sorted_entries, run_boundaries)

    transformed = []
    for entry in sorted_entries:
        entry_id = entry.get("_id")

        # Use explicit run_num if available, otherwise use inferred
        if entry.get("run_num") is not None:
            run_number = entry["run_num"]
        else:
            run_number = inferred_runs.get(entry_id)

        transformed.append({
            "log_id": entry_id,
            "experiment_id": experiment_id,
            "run_number": run_number,
            "timestamp": entry.get("insert_time"),
            "content": entry.get("content"),
            "tags": _format_tags(entry.get("tags")),
            "author": entry.get("author"),
        })

    return transformed


def _format_tags(tags: list[str] | None) -> str | None:
    """Format tags list into a comma-separated string."""
    if not tags:
        return None
    return ",".join(tags)


def _identify_run_boundaries(
    sorted_entries: list[dict[str, Any]],
) -> dict[str, int]:
    """Identify run boundaries based on explicit run numbers."""
    run_boundaries = {}

    for entry in sorted_entries:
        timestamp = entry.get("insert_time")
        run_num = entry.get("run_num")
        content = (entry.get("content", "") or "").lower()

        if run_num is not None:
            run_boundaries[timestamp] = run_num
        elif "run number" in content and "running" in content:
            try:
                parts = content.split(":")[0].split()
                for i, part in enumerate(parts):
                    if part.lower() == "number" and i + 1 < len(parts):
                        run_boundaries[timestamp] = int(parts[i + 1])
                        break
            except (IndexError, ValueError):
                pass

    return run_boundaries


def _infer_run_numbers(
    sorted_entries: list[dict[str, Any]],
    run_boundaries: dict[str, int],
) -> dict[str, int | None]:
    """Infer run numbers for entries without explicit run_num."""
    boundary_times = sorted(run_boundaries.keys())
    boundary_runs = [run_boundaries[time] for time in boundary_times]

    inferred_runs = {}

    for entry in sorted_entries:
        entry_id = entry.get("_id")
        timestamp = entry.get("insert_time")

        # Skip entries with explicit run numbers
        if entry.get("run_num") is not None:
            continue

        inferred_run = None
        for i, boundary_time in enumerate(boundary_times):
            if timestamp < boundary_time:
                if i > 0:
                    inferred_run = boundary_runs[i - 1]
                break
            elif i == len(boundary_times) - 1 or timestamp == boundary_time:
                inferred_run = boundary_runs[i]

        inferred_runs[entry_id] = inferred_run

    return inferred_runs
