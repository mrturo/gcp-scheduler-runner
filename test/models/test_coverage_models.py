"""
Coverage tests for src/models.py (ExecutionSummary, EndpointConfig).
"""

import os
import sys
from test.helpers import (
    endpoint_result_all_success,
    endpoint_result_one_warning,
    endpoint_result_one_error,
)
import pytest
from src.models import ExecutionSummary, EndpointConfig

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

def test_execution_summary_properties():
    """
    Test ExecutionSummary properties for success, warnings, and errors.
    """
    summary_success = ExecutionSummary(**endpoint_result_all_success())
    assert summary_success.success is True
    summary_warnings = ExecutionSummary(
        **endpoint_result_one_warning()
    )
    assert summary_warnings.success is True
    assert summary_warnings.has_warnings is True
    assert summary_warnings.get_http_status() == 207
    summary_errors = ExecutionSummary(
        **endpoint_result_one_error()
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

# All literal appearances of endpoint result dicts must be replaced by
# endpoint_result_all_success(), endpoint_result_one_warning(), or
# endpoint_result_one_error().
