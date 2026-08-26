from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from ai_engine.guardrails import sanitize_payload
from ai_engine.tools.deployments import RecentDeploymentsArgs, get_recent_deployments
from ai_engine.tools.logs import SearchLogsArgs, search_logs
from ai_engine.tools.metrics import ServiceMetricsArgs, get_service_metrics
from ai_engine.tools.runbooks import SearchRunbooksArgs, search_runbooks


class ToolRegistryError(ValueError):
    pass


class UnknownToolError(ToolRegistryError):
    pass


class ToolValidationError(ToolRegistryError):
    pass


class ToolExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    arguments_model: type[BaseModel]
    handler: Callable[..., dict[str, Any]]

    def openai_spec(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.arguments_model.model_json_schema(),
            },
        }


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "get_recent_deployments": ToolDefinition(
        "get_recent_deployments",
        "Read up to three recent local synthetic deployment records for one service.",
        RecentDeploymentsArgs,
        get_recent_deployments,
    ),
    "get_service_metrics": ToolDefinition(
        "get_service_metrics",
        "Read compact local synthetic service metrics and their baseline.",
        ServiceMetricsArgs,
        get_service_metrics,
    ),
    "search_logs": ToolDefinition(
        "search_logs",
        "Search local synthetic logs for one service and return at most five relevant records.",
        SearchLogsArgs,
        search_logs,
    ),
    "search_runbooks": ToolDefinition(
        "search_runbooks",
        "Search the existing local TriageIQ runbook knowledge base and return up to three matches.",
        SearchRunbooksArgs,
        search_runbooks,
    ),
}


def tool_specs() -> list[dict[str, Any]]:
    return [definition.openai_spec() for definition in TOOL_REGISTRY.values()]


def _decode_arguments(arguments: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    try:
        payload = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise ToolValidationError("Tool arguments must be a valid JSON object.") from exc
    if not isinstance(payload, dict):
        raise ToolValidationError("Tool arguments must be a JSON object.")
    return payload


def execute_tool(name: str, arguments: str | dict[str, Any]) -> dict[str, Any]:
    definition = TOOL_REGISTRY.get(name)
    if definition is None:
        raise UnknownToolError(f"Unknown investigation tool: {name}")

    try:
        validated = definition.arguments_model.model_validate(_decode_arguments(arguments))
    except ValidationError as exc:
        raise ToolValidationError(str(exc)) from exc

    try:
        result = definition.handler(**validated.model_dump())
    except Exception as exc:
        raise ToolExecutionError(f"Tool '{name}' failed: {exc}") from exc

    if not isinstance(result, dict):
        raise ToolExecutionError(f"Tool '{name}' returned a non-object result.")
    return sanitize_payload(result)
