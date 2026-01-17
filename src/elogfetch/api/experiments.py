"""Fetch list of recently updated experiments."""

from __future__ import annotations

import re
from typing import Any

from .client import ElogClient
from ..utils import get_logger

logger = get_logger()


def fetch_updated_experiments(
    client: ElogClient,
    offset_secs: int,
    exclude_patterns: list[str] | None = None,
) -> list[str]:
    """Fetch experiment names updated within the specified time period.

    Args:
        client: ElogClient instance
        offset_secs: Number of seconds to look back
        exclude_patterns: List of patterns to exclude (e.g., ["txi*", "test*"])

    Returns:
        List of experiment IDs
    """
    endpoint = "/ws/lgbk/lgbk/ws/experiment_names_updated_within"
    params = {"offset_secs": offset_secs}

    logger.info(f"Fetching experiments updated in last {offset_secs} seconds...")

    data = client.get_public(endpoint, params=params)

    # Extract experiment names from the response
    if isinstance(data, dict) and "value" in data:
        experiments = data["value"]
    elif isinstance(data, list):
        experiments = data
    else:
        logger.error(f"Unexpected response format: {type(data)}")
        return []

    if not experiments:
        logger.info("No experiments found in the specified time period.")
        return []

    logger.info(f"Found {len(experiments)} experiments")

    # Apply filtering if patterns specified
    if exclude_patterns:
        experiments = _filter_experiments(experiments, exclude_patterns)

    return experiments


def _filter_experiments(
    experiments: list[str],
    exclude_patterns: list[str],
) -> list[str]:
    """Filter experiments based on exclude patterns.

    Args:
        experiments: List of experiment IDs
        exclude_patterns: Patterns to exclude (shell-style wildcards)

    Returns:
        Filtered list of experiment IDs
    """
    filtered = []
    excluded_count = 0

    for exp in experiments:
        exclude = False
        for pattern in exclude_patterns:
            # Convert shell-style wildcards to regex
            regex_pattern = pattern.replace("*", ".*").replace("?", ".")
            if re.match(f"^{regex_pattern}$", exp, re.IGNORECASE):
                exclude = True
                excluded_count += 1
                break

        if not exclude:
            filtered.append(exp)

    if excluded_count > 0:
        logger.info(f"Excluded {excluded_count} experiments by patterns {exclude_patterns}")

    logger.info(f"Returning {len(filtered)} experiments after filtering")
    return filtered
