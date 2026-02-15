"""
Test for ExecutionSummary.get_http_status() with all endpoints failed and
total_endpoints > 0 (line 202).
"""

from src.models import ExecutionSummary

def test_execution_summary_all_failed():
    """Test get_http_status returns 500 when all endpoints fail and total_endpoints > 0."""
    summary = ExecutionSummary(
        total_endpoints=2,
        successful=0,
        warnings=0,
        failed=2,
        results=[],
        details={"warnings": [], "errors": []},
        execution_mode="sequential",
    )
    # Should return 500 (all endpoints failed)
    assert summary.get_http_status() == 500
