"""Fetch questionnaire data for an experiment."""

from __future__ import annotations

import re
from typing import Any

from .client import ElogClient
from ..exceptions import APIError
from ..utils import get_logger

logger = get_logger()


def fetch_questionnaire(
    client: ElogClient,
    experiment_id: str,
) -> dict[str, Any] | None:
    """Fetch questionnaire data for an experiment.

    Args:
        client: ElogClient instance
        experiment_id: The experiment ID to fetch

    Returns:
        Dictionary with questionnaire fields, or None on error
    """
    try:
        # First, get experiment info to retrieve PNR
        info_endpoint = f"/ws-kerb/lgbk/lgbk/{experiment_id}/ws/info"
        info_data = client.get(info_endpoint)

        if not info_data.get("success"):
            logger.error(f"Failed to get info for {experiment_id}")
            return None

        info_value = info_data.get("value", {})
        params = info_value.get("params", {})
        proposal_number = params.get("PNR")

        if not proposal_number:
            logger.warning(f"No proposal number (PNR) found for {experiment_id}")
            return None

        # Extract LCLS run number from experiment ID (last 2 digits)
        lcls_run = _extract_lcls_run(experiment_id)
        if not lcls_run:
            logger.warning(f"Could not extract LCLS run from {experiment_id}")
            return None

        # Fetch questionnaire
        questionnaire_endpoint = (
            f"/ws-kerb/questionnaire/ws/proposal/attribute/run{lcls_run}/{proposal_number}"
        )

        questionnaire_data = client.get(questionnaire_endpoint)

        # Parse into individual fields
        fields = _parse_questionnaire_fields(questionnaire_data)

        logger.info(f"Fetched {len(fields)} questionnaire fields for {experiment_id}")

        return {
            "experiment_id": experiment_id,
            "proposal_number": proposal_number,
            "fields": fields,
        }

    except APIError as e:
        logger.error(f"Failed to fetch questionnaire for {experiment_id}: {e}")
        return None


def _extract_lcls_run(experiment_id: str) -> str | None:
    """Extract LCLS run number from experiment ID.

    The LCLS run number is the last two digits of the experiment ID.
    For example, 'tmol1039623' -> '23'
    """
    match = re.search(r"(\d{2})$", experiment_id)
    if match:
        return match.group(1)
    return None


def _parse_questionnaire_fields(
    questionnaire_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Parse questionnaire data into individual field records.

    Args:
        questionnaire_data: Raw questionnaire data from API

    Returns:
        List of field dictionaries with category, field_id, field_name, etc.
    """
    fields = []

    if not questionnaire_data or not isinstance(questionnaire_data, dict):
        return fields

    for category, category_fields in questionnaire_data.items():
        # Skip non-list entries (metadata, etc.)
        if not isinstance(category_fields, list):
            continue

        for field_data in category_fields:
            if not isinstance(field_data, dict):
                continue

            field_id = field_data.get("id")
            if not field_id:
                continue

            # Extract field name by removing category prefix
            field_name = field_id.replace(f"{category}-", "") if field_id else None

            fields.append({
                "category": category,
                "field_id": field_id,
                "field_name": field_name,
                "field_value": field_data.get("val"),
                "modified_time": field_data.get("modified_time"),
                "modified_uid": field_data.get("modified_uid"),
            })

    return fields
