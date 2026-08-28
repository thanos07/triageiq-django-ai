import pytest
from pydantic import ValidationError

from ai_engine.schemas import InvestigationResult
from ai_engine.tools import (
    TOOL_REGISTRY,
    ToolValidationError,
    UnknownToolError,
    execute_tool,
    get_recent_deployments,
    get_service_metrics,
    search_logs,
    search_runbooks,
    tool_specs,
)


def test_registry_exposes_only_four_read_tools():
    expected = {
        "get_recent_deployments",
        "get_service_metrics",
        "search_logs",
        "search_runbooks",
    }
    assert set(TOOL_REGISTRY) == expected
    specs = tool_specs()
    assert len(specs) == 4
    assert {item["function"]["name"] for item in specs} == expected


def test_recent_deployments_are_service_scoped_and_compact():
    result = get_recent_deployments(" profile-api ")
    assert result["service_name"] == "profile-api"
    assert result["found"] is True
    assert len(result["deployments"]) <= 3
    assert result["deployments"][0]["version"] == "8.2.0"


def test_metrics_return_current_and_baseline_values():
    result = get_service_metrics("search-api")
    metrics = {item["name"]: item for item in result["values"]}
    assert result["found"] is True
    assert metrics["cpu_utilization_percent"]["current"] == 98
    assert metrics["p99_latency_ms"]["current"] == 12300


def test_log_search_filters_locally_and_caps_results():
    result = search_logs("billing-worker", "invalid password secret rotation")
    assert result["found"] is True
    assert 1 <= len(result["matches"]) <= 5
    text = " ".join(item["message"] for item in result["matches"]).lower()
    assert "invalid password" in text or "secret" in text


def test_unknown_service_becomes_an_evidence_gap():
    result = execute_tool("get_service_metrics", {"service_name": "unknown-demo-service"})
    assert result["found"] is False
    assert result["values"] == []


def test_existing_runbook_retrieval_is_reused():
    result = search_runbooks("HTTP 5xx error spike immediately after deployment release")
    assert 1 <= len(result["matches"]) <= 3
    assert all(item["id"].startswith("rb-") for item in result["matches"])


def test_registry_rejects_extra_or_invalid_arguments():
    with pytest.raises(ToolValidationError):
        execute_tool("get_service_metrics", {"service_name": "profile-api", "command": "rm -rf /"})
    with pytest.raises(ToolValidationError):
        execute_tool("search_logs", {"service_name": "profile-api", "query": ""})


def test_unknown_tool_name_is_rejected_without_dynamic_execution():
    with pytest.raises(UnknownToolError):
        execute_tool("__import__('os').system", {"service_name": "profile-api"})


def test_investigation_result_requires_bounded_confidence():
    valid = InvestigationResult(
        observations=["Error rate rose after release."],
        tools_used=["get_recent_deployments", "get_service_metrics"],
        leading_hypothesis="Recent application regression",
        supporting_evidence=["Release 8.2.0 precedes the 5xx spike."],
        missing_evidence=["Request trace sample"],
        confidence=0.86,
    )
    assert valid.confidence == 0.86
    with pytest.raises(ValidationError):
        InvestigationResult(confidence=1.1)


def test_recent_deployments_distinguish_known_service_from_deployment_evidence():
    result = get_recent_deployments("orders-api")
    assert result["service_found"] is True
    assert result["found"] is False
    assert result["deployments"] == []
