from types import SimpleNamespace

import pytest

from ai_engine.agents.investigation import InvestigationAgent
from ai_engine.provider import ToolCallRequest, ToolTurnResult


@pytest.fixture
def context():
    return {
        "incident": {
            "reference": "INC-DEMO",
            "title": "Profile API error spike immediately after release 8.2.0",
            "description": "HTTP 5xx increased immediately after deployment of release 8.2.0.",
            "service_name": "profile-api",
            "environment": "production",
            "reported_severity": "high",
            "business_impact": "Customers intermittently cannot update profiles.",
            "extracted_context": {},
            "information_gaps": [],
        },
        "severity": {
            "level": "high",
            "category": "availability",
            "confidence": 0.9,
        },
    }


@pytest.mark.django_db
def test_mock_mode_uses_deterministic_read_only_tools(settings, context):
    settings.AI_MODE = "mock"
    settings.AI_INVESTIGATION_MAX_TOOL_CALLS = 3

    run = InvestigationAgent().run(context)

    assert run.execution_mode == "mock"
    assert run.model_name == "deterministic-investigation-v1"
    assert 1 <= len(run.tool_executions) <= 3
    assert all(item.status == "success" for item in run.tool_executions)
    assert "get_service_metrics" in run.output.tools_used
    assert "search_logs" in run.output.tools_used
    assert "get_recent_deployments" in run.output.tools_used
    assert "deployment" in run.output.leading_hypothesis.lower()
    assert 0 <= run.output.confidence <= 1


@pytest.mark.django_db
def test_live_without_key_is_explicit_fallback_not_mock(settings, context):
    settings.AI_MODE = "live"
    settings.AI_API_KEY = ""
    settings.AI_INVESTIGATION_MAX_TOOL_CALLS = 3

    run = InvestigationAgent().run(context)

    assert run.execution_mode == "fallback"
    assert run.model_name == "deterministic-investigation-fallback-v1"
    assert "AI_API_KEY" in run.error_message
    assert run.tool_executions


@pytest.mark.django_db
def test_live_model_selects_tool_then_returns_valid_investigation(
    settings,
    context,
    monkeypatch,
):
    settings.AI_MODE = "live"
    settings.AI_API_KEY = "test-key"
    settings.AI_INVESTIGATION_MAX_TOOL_CALLS = 3

    calls = {"count": 0}

    def fake_init(self):
        pass

    def fake_turn(self, *, messages, tools=None):
        calls["count"] += 1
        if calls["count"] == 1:
            assert tools
            return ToolTurnResult(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="call-1",
                        name="get_recent_deployments",
                        arguments='{"service_name":"profile-api"}',
                    )
                ],
                assistant_message={
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "get_recent_deployments",
                                "arguments": '{"service_name":"profile-api"}',
                            },
                        }
                    ],
                },
                model_name="openai/gpt-oss-20b",
                latency_ms=12,
                retry_count=0,
            )

        assert any(message.get("role") == "tool" for message in messages)
        return ToolTurnResult(
            content=(
                '{"observations":["Release 8.2.0 immediately precedes the failure."],'
                '"tools_used":["search_logs"],'
                '"leading_hypothesis":"Release 8.2.0 regression",'
                '"supporting_evidence":["Deployment timing matches the error spike."],'
                '"missing_evidence":["A request trace sample"],'
                '"confidence":0.88}'
            ),
            tool_calls=[],
            assistant_message={"role": "assistant", "content": ""},
            model_name="openai/gpt-oss-20b",
            latency_ms=10,
            retry_count=0,
        )

    monkeypatch.setattr(
        "ai_engine.agents.investigation.OpenAICompatibleProvider.__init__",
        fake_init,
    )
    monkeypatch.setattr(
        "ai_engine.agents.investigation.OpenAICompatibleProvider.complete_tool_turn",
        fake_turn,
    )

    run = InvestigationAgent().run(context)

    assert run.execution_mode == "live"
    assert run.model_name == "openai/gpt-oss-20b"
    assert calls["count"] == 2
    assert len(run.tool_executions) == 1
    assert run.tool_executions[0].tool_name == "get_recent_deployments"
    # Audit integrity: actual tools override any invented model-authored tools_used list.
    assert run.output.tools_used == ["get_recent_deployments"]
    assert run.output.confidence == 0.88


@pytest.mark.django_db
def test_live_agent_enforces_tool_budget(settings, context, monkeypatch):
    settings.AI_MODE = "live"
    settings.AI_API_KEY = "test-key"
    settings.AI_INVESTIGATION_MAX_TOOL_CALLS = 2

    calls = {"count": 0}

    def fake_init(self):
        pass

    def fake_turn(self, *, messages, tools=None):
        calls["count"] += 1
        if calls["count"] <= 2:
            assert tools
            tool_name = "get_service_metrics" if calls["count"] == 1 else "search_logs"
            arguments = (
                '{"service_name":"profile-api"}'
                if tool_name == "get_service_metrics"
                else '{"service_name":"profile-api","query":"500 release"}'
            )
            call_id = f"call-{calls['count']}"
            return ToolTurnResult(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id=call_id,
                        name=tool_name,
                        arguments=arguments,
                    )
                ],
                assistant_message={
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {"name": tool_name, "arguments": arguments},
                        }
                    ],
                },
                model_name="openai/gpt-oss-20b",
                latency_ms=5,
                retry_count=0,
            )

        # Once the budget is exhausted the agent removes tools from the final turn.
        assert tools is None
        return ToolTurnResult(
            content=(
                '{"observations":["Metrics and logs correlate with the failure."],'
                '"tools_used":[],'
                '"leading_hypothesis":"Application regression",'
                '"supporting_evidence":["5xx spike","post-release errors"],'
                '"missing_evidence":[],'
                '"confidence":0.81}'
            ),
            tool_calls=[],
            assistant_message={"role": "assistant", "content": ""},
            model_name="openai/gpt-oss-20b",
            latency_ms=4,
            retry_count=0,
        )

    monkeypatch.setattr(
        "ai_engine.agents.investigation.OpenAICompatibleProvider.__init__",
        fake_init,
    )
    monkeypatch.setattr(
        "ai_engine.agents.investigation.OpenAICompatibleProvider.complete_tool_turn",
        fake_turn,
    )

    run = InvestigationAgent().run(context)

    assert run.execution_mode == "live"
    assert len(run.tool_executions) == 2
    assert [item.tool_name for item in run.tool_executions] == [
        "get_service_metrics",
        "search_logs",
    ]
    assert calls["count"] == 3


@pytest.mark.django_db
def test_invalid_live_final_output_falls_back_safely(settings, context, monkeypatch):
    settings.AI_MODE = "live"
    settings.AI_API_KEY = "test-key"
    settings.AI_INVESTIGATION_MAX_TOOL_CALLS = 1

    calls = {"count": 0}

    def fake_init(self):
        pass

    def fake_turn(self, *, messages, tools=None):
        calls["count"] += 1
        if calls["count"] == 1:
            return ToolTurnResult(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="call-1",
                        name="get_service_metrics",
                        arguments='{"service_name":"profile-api"}',
                    )
                ],
                assistant_message={
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "get_service_metrics",
                                "arguments": '{"service_name":"profile-api"}',
                            },
                        }
                    ],
                },
                model_name="openai/gpt-oss-20b",
                latency_ms=5,
                retry_count=0,
            )
        return ToolTurnResult(
            content="not-json",
            tool_calls=[],
            assistant_message={"role": "assistant", "content": "not-json"},
            model_name="openai/gpt-oss-20b",
            latency_ms=5,
            retry_count=0,
        )

    monkeypatch.setattr(
        "ai_engine.agents.investigation.OpenAICompatibleProvider.__init__",
        fake_init,
    )
    monkeypatch.setattr(
        "ai_engine.agents.investigation.OpenAICompatibleProvider.complete_tool_turn",
        fake_turn,
    )

    run = InvestigationAgent().run(context)

    assert run.execution_mode == "fallback"
    assert run.model_name == "deterministic-investigation-fallback-v1"
    assert run.tool_executions
    assert run.error_message



@pytest.mark.django_db
def test_schema_invalid_live_final_is_repaired_once(settings, context, monkeypatch):
    settings.AI_MODE = "live"
    settings.AI_API_KEY = "test-key"
    settings.AI_INVESTIGATION_MAX_TOOL_CALLS = 1

    calls = {"count": 0}

    def fake_init(self):
        pass

    def fake_turn(self, *, messages, tools=None):
        calls["count"] += 1
        if calls["count"] == 1:
            assert tools
            return ToolTurnResult(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="call-1",
                        name="get_recent_deployments",
                        arguments='{"service_name":"profile-api"}',
                    )
                ],
                assistant_message={
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "get_recent_deployments",
                                "arguments": '{"service_name":"profile-api"}',
                            },
                        }
                    ],
                },
                model_name="openai/gpt-oss-20b",
                latency_ms=5,
                retry_count=0,
            )

        if calls["count"] == 2:
            assert tools is None
            # Mirrors the real Groq failure we observed: a list field was emitted
            # as numbered prose in a single JSON string.
            return ToolTurnResult(
                content=(
                    '{"observations":"1) Release 8.2.0 precedes the failure.",'
                    '"tools_used":["get_recent_deployments"],'
                    '"leading_hypothesis":"Release regression",'
                    '"supporting_evidence":["Deployment timing matches."],'
                    '"missing_evidence":[],"confidence":0.86}'
                ),
                tool_calls=[],
                assistant_message={"role": "assistant", "content": "bad-shape"},
                model_name="openai/gpt-oss-20b",
                latency_ms=5,
                retry_count=0,
            )

        assert calls["count"] == 3
        assert tools is None
        assert any(
            "observations=array[string]" in str(message.get("content", ""))
            for message in messages
        )
        return ToolTurnResult(
            content=(
                '{"observations":["Release 8.2.0 precedes the failure."],'
                '"tools_used":["invented-tool"],'
                '"leading_hypothesis":"Release regression",'
                '"supporting_evidence":["Deployment timing matches."],'
                '"missing_evidence":[],"confidence":0.86}'
            ),
            tool_calls=[],
            assistant_message={"role": "assistant", "content": "repaired"},
            model_name="openai/gpt-oss-20b",
            latency_ms=5,
            retry_count=0,
        )

    monkeypatch.setattr(
        "ai_engine.agents.investigation.OpenAICompatibleProvider.__init__",
        fake_init,
    )
    monkeypatch.setattr(
        "ai_engine.agents.investigation.OpenAICompatibleProvider.complete_tool_turn",
        fake_turn,
    )

    run = InvestigationAgent().run(context)

    assert run.execution_mode == "live"
    assert calls["count"] == 3
    assert len(run.tool_executions) == 1
    assert run.tool_executions[0].tool_name == "get_recent_deployments"
    assert run.output.observations == ["Release 8.2.0 precedes the failure."]
    # The persisted audit remains authoritative after the repair turn.
    assert run.output.tools_used == ["get_recent_deployments"]
    assert run.output.confidence == 0.86
