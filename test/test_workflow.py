"""Pytest test suite for the incident response workflow"""

import pytest
import logging
from src.agents.supervisor import create_workflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def workflow():
    """Create workflow instance (reused across tests in this module)"""
    logging.info("Creating workflow instance...")
    return create_workflow()


@pytest.fixture
def sample_database_timeout_logs():
    """Sample logs for database timeout incident"""
    return """
[2024-01-15 10:23:45] ERROR: Connection timeout after 30s
[2024-01-15 10:23:45] ERROR: Failed to connect to database: postgresql://db:5432
[2024-01-15 10:23:46] ERROR: Connection pool exhausted (50/50 connections in use)
[2024-01-15 10:23:47] ERROR: 504 Gateway Timeout
[2024-01-15 10:23:48] ERROR: Query timeout: SELECT * FROM users WHERE email = 'test@example.com'
[2024-01-15 10:23:49] WARN: Retrying connection attempt 3/5
[2024-01-15 10:23:50] ERROR: All backend services unresponsive
"""


@pytest.fixture
def sample_oom_logs():
    """Sample logs for Out of Memory incident"""
    return """
[2024-01-15 14:30:12] ERROR: java.lang.OutOfMemoryError: Java heap space
[2024-01-15 14:30:12] ERROR: Container killed due to memory limit
[2024-01-15 14:30:13] WARN: Memory usage: 3.8GB / 4GB (95%)
[2024-01-15 14:30:14] ERROR: Pod evicted: memory limit exceeded
[2024-01-15 14:30:15] ERROR: Application crashed with exit code 137
"""


# ============================================================================
# Integration Tests
# ============================================================================

def test_workflow_end_to_end(workflow, sample_database_timeout_logs):
    """Test complete workflow execution with database timeout scenario"""

    # Execute workflow
    result = workflow.invoke({
        "input_log": sample_database_timeout_logs,
        "service_name": "API Gateway",
        "severity": "Critical"
    })

    # Assert workflow completed without errors
    assert result is not None
    assert result.get('errors', []) == [] or len(result.get('errors', [])) == 0

    # Assert log analysis outputs
    assert 'log_analysis' in result
    assert 'search_query' in result

    # Assert retrieval outputs
    assert 'similar_incidents' in result
    assert 'relevant_runbooks' in result
    assert isinstance(result['similar_incidents'], list)
    assert isinstance(result['relevant_runbooks'], list)

    # Assert diagnostic outputs
    assert 'root_cause' in result
    assert result['root_cause'] != 'Unable to determine'
    assert 'confidence' in result
    assert 0 <= result['confidence'] <= 1
    assert 'diagnostic_reasoning' in result

    # Assert action plan outputs
    assert 'action_plan' in result
    assert 'resolution_steps' in result or 'action_plan' in result

    # Log results for visibility
    logging.info(f"Root Cause: {result['root_cause']}")
    logging.info(f"Confidence: {result['confidence']:.0%}")
    logging.info(f"Similar Incidents: {len(result['similar_incidents'])}")
    logging.info(f"Relevant Runbooks: {len(result['relevant_runbooks'])}")


def test_workflow_with_oom_scenario(workflow, sample_oom_logs):
    """Test workflow with Out of Memory scenario"""

    result = workflow.invoke({
        "input_log": sample_oom_logs,
        "service_name": "Application Server",
        "severity": "High"
    })

    # Basic assertions
    assert result is not None
    assert 'root_cause' in result
    assert result['root_cause'] != 'Unable to determine'
    assert result['confidence'] > 0

    # Check if OOM is detected
    root_cause_lower = result['root_cause'].lower()
    assert 'memory' in root_cause_lower or 'oom' in root_cause_lower

    logging.info(f"OOM Test - Root Cause: {result['root_cause']}")


# ============================================================================
# Component Tests
# ============================================================================

def test_workflow_log_analysis_step(workflow, sample_database_timeout_logs):
    """Test that log analysis step produces expected outputs"""

    result = workflow.invoke({
        "input_log": sample_database_timeout_logs,
        "service_name": "API Gateway",
        "severity": "Critical"
    })

    # Check log analysis outputs
    assert 'log_analysis' in result
    log_analysis = result['log_analysis']

    assert 'summary' in log_analysis or isinstance(log_analysis, dict)
    assert 'search_query' in result
    assert len(result['search_query']) > 0


def test_workflow_retrieval_step(workflow, sample_database_timeout_logs):
    """Test that retrieval step finds relevant context"""

    result = workflow.invoke({
        "input_log": sample_database_timeout_logs,
        "service_name": "API Gateway",
        "severity": "Critical"
    })

    # Check retrieval found something
    similar_incidents = result.get('similar_incidents', [])
    relevant_runbooks = result.get('relevant_runbooks', [])

    # Should find at least some context (may be 0 if DB is empty, but structure should exist)
    assert isinstance(similar_incidents, list)
    assert isinstance(relevant_runbooks, list)

    logging.info(f"Retrieved {len(similar_incidents)} incidents, {len(relevant_runbooks)} runbooks")


def test_workflow_diagnostic_step(workflow, sample_database_timeout_logs):
    """Test that diagnostic step provides analysis"""

    result = workflow.invoke({
        "input_log": sample_database_timeout_logs,
        "service_name": "API Gateway",
        "severity": "Critical"
    })

    # Check diagnostic outputs
    assert 'root_cause' in result
    assert isinstance(result['root_cause'], str)
    assert len(result['root_cause']) > 0

    assert 'confidence' in result
    assert isinstance(result['confidence'], (int, float))
    assert 0 <= result['confidence'] <= 1


def test_workflow_action_step(workflow, sample_database_timeout_logs):
    """Test that action planning step provides resolution steps"""

    result = workflow.invoke({
        "input_log": sample_database_timeout_logs,
        "service_name": "API Gateway",
        "severity": "Critical"
    })

    # Check action plan exists
    assert 'action_plan' in result
    action_plan = result['action_plan']

    assert isinstance(action_plan, dict)
    # Should have some form of actions
    assert 'immediate_actions' in action_plan or 'resolution_steps' in result


# ============================================================================
# Edge Cases & Error Handling
# ============================================================================

def test_workflow_with_minimal_logs(workflow):
    """Test workflow with minimal log input"""

    minimal_logs = "[2024-01-15 10:00:00] ERROR: Something went wrong"

    result = workflow.invoke({
        "input_log": minimal_logs,
        "service_name": "Unknown Service",
        "severity": "Medium"
    })

    # Should still complete, even with minimal info
    assert result is not None
    assert 'root_cause' in result


def test_workflow_with_empty_service_name(workflow, sample_database_timeout_logs):
    """Test workflow handles empty service name"""

    result = workflow.invoke({
        "input_log": sample_database_timeout_logs,
        "service_name": "",
        "severity": "Medium"
    })

    # Should still work
    assert result is not None
    assert 'root_cause' in result


# ============================================================================
# Parameterized Tests
# ============================================================================

@pytest.mark.parametrize("severity", ["Critical", "High", "Medium", "Low"])
def test_workflow_different_severities(workflow, sample_database_timeout_logs, severity):
    """Test workflow handles different severity levels"""

    result = workflow.invoke({
        "input_log": sample_database_timeout_logs,
        "service_name": "API Gateway",
        "severity": severity
    })

    assert result is not None
    assert 'root_cause' in result
    logging.info(f"Severity {severity}: {result['root_cause']}")


# ============================================================================
# Performance Tests
# ============================================================================

def test_workflow_execution_time(workflow, sample_database_timeout_logs):
    """Test that workflow completes in reasonable time"""
    import time

    start_time = time.time()
    result = workflow.invoke({
        "input_log": sample_database_timeout_logs,
        "service_name": "API Gateway",
        "severity": "Critical"
    })
    execution_time = time.time() - start_time

    assert result is not None
    assert execution_time < 60, f"Workflow took {execution_time}s, should be < 60s"
    logging.info(f"Workflow execution time: {execution_time:.2f}s")


# ============================================================================
# Display Helper (for manual test runs)
# ============================================================================

def display_results(result):
    """Helper function to display test results in readable format"""
    print("\n" + "=" * 80)
    print("WORKFLOW TEST RESULTS")
    print("=" * 80)

    print(f"\n✓ Root Cause: {result.get('root_cause', 'Unknown')}")
    print(f"✓ Confidence: {result.get('confidence', 0):.0%}")
    print(f"✓ Estimated Resolution Time: {result.get('estimated_time', 'Unknown')}")

    print(f"\n✓ Similar Incidents Found: {len(result.get('similar_incidents', []))}")
    print(f"✓ Relevant Runbooks Found: {len(result.get('relevant_runbooks', []))}")

    action_plan = result.get('action_plan', {})
    immediate_actions = action_plan.get('immediate_actions', [])
    print(f"✓ Immediate Actions: {len(immediate_actions)} steps")

    if immediate_actions:
        print("\nFirst Immediate Action:")
        first_action = immediate_actions[0]
        print(f"  - {first_action.get('action', 'N/A')}")
        if first_action.get('commands'):
            print(f"  - Commands: {first_action['commands'][0]}")

    if result.get('errors'):
        print("\n⚠ Errors encountered:")
        for error in result['errors']:
            print(f"  - {error}")

    print("\n" + "=" * 80)


# ============================================================================
# Manual Test Runner (optional)
# ============================================================================

if __name__ == "__main__":
    # This allows running the file directly for quick testing
    pytest.main([__file__, "-v", "-s"])
