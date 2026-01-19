"""
Coverage tests for src/models.py (ExecutionSummary, EndpointConfig).
"""

import os
import sys

import pytest
from src.models import ExecutionSummary, EndpointConfig

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

def test_execution_summary_properties():
    """
    Test ExecutionSummary properties for success, warnings, and errors.
    """
    summary_success = ExecutionSummary(
        total_endpoints=3,
        successful=3,
        warnings=0,
        failed=0,
        results=[],
        details={"warnings": [], "errors": []},
    )
    assert summary_success.success is True
    summary_warnings = ExecutionSummary(
        total_endpoints=3,
        successful=2,
        warnings=1,
        failed=0,
        results=[],
        details={"warnings": [{"endpoint": "http://example.com"}], "errors": []},
    )
    assert summary_warnings.success is False
    assert summary_warnings.has_warnings is True
    assert summary_warnings.get_http_status() == 207
    summary_errors = ExecutionSummary(
        total_endpoints=3,
        successful=2,
        warnings=0,
        failed=1,
        results=[],
        details={"warnings": [], "errors": [{"endpoint": "http://example.com/error"}]},
    )
    assert summary_errors.success is False
    assert summary_errors.has_errors is True
    assert summary_errors.get_http_status() == 500

def test_endpoint_config_invalid_type():
    """
    Test EndpointConfig.from_config with invalid type raises ValueError.
    """
    with pytest.raises(ValueError, match="Invalid endpoint configuration type"):
        EndpointConfig.from_config(12345)
