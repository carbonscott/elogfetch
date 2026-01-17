"""Fetch experiment information."""

from __future__ import annotations

import re
from typing import Any

from .client import ElogClient
from ..exceptions import APIError
from ..utils import get_logger

logger = get_logger()


def fetch_experiment_info(
    client: ElogClient,
    experiment_id: str,
) -> dict[str, Any] | None:
    """Fetch experiment information from the elog API.

    Args:
        client: ElogClient instance
        experiment_id: The experiment ID to fetch

    Returns:
        Dictionary with experiment info formatted for database, or None on error
    """
    endpoint = f"/ws-kerb/lgbk/lgbk/{experiment_id}/ws/info"

    try:
        data = client.get(endpoint)

        if not data.get("success"):
            logger.error(f"API returned success=False for {experiment_id}")
            return None

        raw_info = data.get("value")
        if not raw_info:
            logger.error(f"No value in response for {experiment_id}")
            return None

        return _convert_to_db_format(experiment_id, raw_info)

    except APIError as e:
        logger.error(f"Failed to fetch info for {experiment_id}: {e}")
        return None


def _parse_contact_info(contact_info: str | None) -> tuple[str | None, str | None]:
    """Parse the contact_info string to extract PI name and email.

    Args:
        contact_info: Contact info string (e.g., "John Doe (john@example.com)")

    Returns:
        Tuple of (pi_name, pi_email)
    """
    if not contact_info:
        return None, None

    # Try to match pattern: name (email)
    match = re.search(r"(.*?)\s*\((.*?)\)", contact_info)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # If no email found, return the name only
    return contact_info.strip(), None


def _convert_to_db_format(
    experiment_id: str,
    raw_info: dict[str, Any],
) -> dict[str, Any]:
    """Convert API response to database format.

    Args:
        experiment_id: The experiment ID
        raw_info: Raw info from the API

    Returns:
        Dictionary formatted for the database
    """
    pi, pi_email = _parse_contact_info(raw_info.get("contact_info"))
    params = raw_info.get("params", {})

    return {
        "experiment_id": raw_info.get("_id") or experiment_id,
        "name": raw_info.get("name"),
        "instrument": raw_info.get("instrument"),
        "start_time": raw_info.get("start_time"),
        "end_time": raw_info.get("end_time"),
        "pi": pi,
        "pi_email": pi_email,
        "leader_account": raw_info.get("leader_account"),
        "description": raw_info.get("description"),
        "slack_channels": params.get("slack_channels"),
        "analysis_queues": params.get("analysis_queues"),
        "urawi_proposal": params.get("PNR"),
    }
