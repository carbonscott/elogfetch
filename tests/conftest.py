"""Shared fixtures for elogfetch tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_experiment_data():
    """Sample experiment data for testing."""
    return {
        "experiment_id": "cxic00123",
        "name": "CXI Test Experiment",
        "instrument": "CXI",
        "start_time": "2024-01-15T10:00:00",
        "end_time": "2024-01-20T18:00:00",
        "pi": "John Smith",
        "pi_email": "john.smith@example.com",
        "leader_account": "jsmith",
        "description": "Test experiment for unit testing",
        "slack_channels": "#cxi-test",
        "analysis_queues": "cxiq",
        "urawi_proposal": "LR12345",
    }


@pytest.fixture
def sample_logbook_entries():
    """Sample logbook entries for testing."""
    return [
        {
            "experiment_id": "cxic00123",
            "run_number": 1,
            "timestamp": "2024-01-15T10:30:00",
            "content": "Started first run",
            "tags": "start,calibration",
            "author": "jsmith",
        },
        {
            "experiment_id": "cxic00123",
            "run_number": 2,
            "timestamp": "2024-01-15T11:00:00",
            "content": "Second run with new settings",
            "tags": "data,production",
            "author": "jsmith",
        },
        {
            "experiment_id": "cxic00123",
            "run_number": None,
            "timestamp": "2024-01-15T14:00:00",
            "content": "General notes about the experiment",
            "tags": "notes",
            "author": "asmith",
        },
    ]


@pytest.fixture
def sample_questionnaire_data():
    """Sample questionnaire data for testing."""
    return {
        "experiment_id": "cxic00123",
        "proposal_number": "LR12345",
        "fields": [
            {
                "category": "sample",
                "field_id": "sample_name",
                "field_name": "Sample Name",
                "field_value": "Protein Crystal X",
                "modified_time": "2024-01-14T09:00:00",
                "modified_uid": "jsmith",
            },
            {
                "category": "sample",
                "field_id": "sample_type",
                "field_name": "Sample Type",
                "field_value": "Protein",
                "modified_time": "2024-01-14T09:00:00",
                "modified_uid": "jsmith",
            },
        ],
    }


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing."""
    return {
        "experiment_id": "cxic00123",
        "workflows": [
            {
                "mongo_id": "abc123",
                "name": "auto_sfx",
                "executable": "/cds/sw/ds/ana/auto_sfx.sh",
                "trigger": "manual",
                "location": "S3DF",
                "parameters": {"resolution": 2.5},
                "run_param_name": "run",
                "run_param_value": "latest",
                "run_as_user": "jsmith",
            },
        ],
    }


@pytest.fixture
def sample_runtable_data():
    """Sample run table data for testing."""
    return {
        "experiment_id": "cxic00123",
        "data_production": [
            {
                "run_number": 1,
                "start_time": "2024-01-15T10:00:00",
                "end_time": "2024-01-15T10:30:00",
                "n_events": 10000,
                "n_damaged": 5,
                "n_dropped": 2,
                "prod_start": "2024-01-15T10:00:00",
                "prod_end": "2024-01-15T10:30:00",
            },
            {
                "run_number": 2,
                "start_time": "2024-01-15T11:00:00",
                "end_time": "2024-01-15T12:00:00",
                "n_events": 25000,
                "n_damaged": 10,
                "n_dropped": 3,
                "prod_start": "2024-01-15T11:00:00",
                "prod_end": "2024-01-15T12:00:00",
            },
        ],
        "detectors": [
            {"run_number": 1, "cspad": "Recorded", "epix": "Not Recorded"},
            {"run_number": 2, "cspad": "Recorded", "epix": "Recorded"},
        ],
    }


@pytest.fixture
def sample_file_manager_data():
    """Sample file manager data for testing."""
    return {
        "experiment_id": "cxic00123",
        "file_manager_records": [
            {
                "run_number": 1,
                "number_of_files": 10,
                "total_size_bytes": 1073741824,  # 1 GB
            },
            {
                "run_number": 2,
                "number_of_files": 25,
                "total_size_bytes": 2684354560,  # 2.5 GB
            },
        ],
    }
