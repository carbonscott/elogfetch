"""Fetch workflow definitions for an experiment."""

from __future__ import annotations

from typing import Any

from .client import ElogClient
from ..exceptions import APIError
from ..utils import get_logger

logger = get_logger()


def fetch_workflow(
    client: ElogClient,
    experiment_id: str,
) -> dict[str, Any] | None:
    """Fetch workflow definitions for an experiment.

    Args:
        client: ElogClient instance
        experiment_id: The experiment ID to fetch

    Returns:
        Dictionary with workflow definitions, or None on error
    """
    endpoint = f"/ws-kerb/lgbk/lgbk/{experiment_id}/ws/workflow_definitions"

    try:
        data = client.get(endpoint)

        if not data.get("success"):
            logger.error(f"API returned success=False for workflow of {experiment_id}")
            return None

        workflows = data.get("value", [])
        logger.info(f"Fetched {len(workflows)} workflows for {experiment_id}")

        return {
            "experiment_id": experiment_id,
            "workflows": [_format_workflow(w) for w in workflows],
        }

    except APIError as e:
        logger.error(f"Failed to fetch workflow for {experiment_id}: {e}")
        return None


def _format_workflow(raw_workflow: dict[str, Any]) -> dict[str, Any]:
    """Format a workflow definition for storage."""
    return {
        "mongo_id": raw_workflow.get("_id"),
        "name": raw_workflow.get("name"),
        "executable": raw_workflow.get("executable"),
        "trigger": raw_workflow.get("trigger"),
        "location": raw_workflow.get("location"),
        "parameters": raw_workflow.get("parameters"),
        "run_param_name": raw_workflow.get("run_param_name"),
        "run_param_value": raw_workflow.get("run_param_value"),
        "run_as_user": raw_workflow.get("run_as_user"),
    }
