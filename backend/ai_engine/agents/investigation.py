from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from django.conf import settings
from pydantic import ValidationError

from ai_engine.prompts import INVESTIGATION_SYSTEM
from ai_engine.provider import (
    OpenAICompatibleProvider,
    ProviderError,
    extract_json_object,
)
from ai_engine.schemas import InvestigationResult
from ai_engine.tools import (
    ToolExecutionError,
    ToolRegistryError,
    execute_tool,
    tool_specs,
)


@dataclass(slots=True)
class InvestigationToolRun:
    sequence: int
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    status: str
    latency_ms: int
    execution_mode: str
    error_message: str = ""


@dataclass(slots=True)
class InvestigationRun:
    output: InvestigationResult
    model_name: str
    latency_ms: int
    retry_count: int
    execution_mode: str
    error_message: str = ""
    tool_executions: list[InvestigationToolRun] = field(default_factory=list)


ToolObserver = Callable[[InvestigationToolRun], None]


class InvestigationAgent:
    """Bounded evidence-gathering agent.

    Live mode lets the model choose from an explicit read-only tool registry.
    Mock/fallback modes stay deterministic and require no external service.
    """

    stage = "investigation"

    @staticmethod
    def _incident(context: dict[str, Any]) -> dict[str, Any]:
        incident = context.get("incident", {}) or {}
        return incident if isinstance(incident, dict) else {}

    @staticmethod
    def _tool_budget() -> int:
        raw = getattr(settings, "AI_INVESTIGATION_MAX_TOOL_CALLS", 3)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = 3
        return max(1, min(value, 5))

    @staticmethod
    def _safe_arguments(raw: str) -> dict[str, Any]:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {"_invalid_json": raw[:240]}
        return value if isinstance(value, dict) else {"_invalid_arguments": value}

    def build_prompt(self, context: dict[str, Any]) -> str:
        incident = self._incident(context)
        payload = {
            "incident": {
                "reference": incident.get("reference", ""),
                "title": incident.get("title", ""),
                "description": incident.get("description", ""),
                "service_name": incident.get("service_name", ""),
                "environment": incident.get("environment", ""),
                "reported_severity": incident.get("reported_severity", ""),
                "business_impact": incident.get("business_impact", ""),
                "extracted_context": incident.get("extracted_context", {}),
                "information_gaps": incident.get("information_gaps", []),
            },
            "severity": context.get("severity", {}) or {},
            "tool_budget": self._tool_budget(),
        }
        return json.dumps(payload, indent=2, default=str)

    def _mock_plan(self, context: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        incident = self._incident(context)
        service = str(incident.get("service_name", "")).strip()
        text = " ".join(
            str(value)
            for value in (
                incident.get("title", ""),
                incident.get("description", ""),
                incident.get("business_impact", ""),
            )
            if value
        ).lower()

        plan: list[tuple[str, dict[str, Any]]] = []
        if service:
            plan.append(("get_service_metrics", {"service_name": service}))

        query = " ".join(
            word.strip(".,:;()[]{}")
            for word in text.split()
            if len(word.strip(".,:;()[]{}")) >= 4
        )[:220] or "error failure timeout"
        if service:
            plan.append(("search_logs", {"service_name": service, "query": query}))

        change_signals = (
            "deploy",
            "release",
            "rollout",
            "rotation",
            "config",
            "feature",
            "version",
            "secret",
            "key",
            "certificate",
            "new ",
            "changed",
            "updated",
            "reduced",
            "disabled",
            "enabled",
        )
        if service and any(signal in text for signal in change_signals):
            plan.append(("get_recent_deployments", {"service_name": service}))
        else:
            plan.append(("search_runbooks", {"query": text[:280] or service or "incident"}))

        return plan[: self._tool_budget()]

    @staticmethod
    def _summarize_tool_result(tool_name: str, result: dict[str, Any]) -> list[str]:
        observations: list[str] = []
        if not result.get("found", True):
            return [f"{tool_name}: no local operational evidence was found for the requested service."]

        if tool_name == "get_recent_deployments":
            for item in result.get("deployments", [])[:2]:
                observations.append(
                    f"Deployment {item.get('version', 'unknown')} at {item.get('deployed_at', 'unknown time')}: "
                    f"{item.get('change_summary', 'no summary')}."
                )
        elif tool_name == "get_service_metrics":
            for item in result.get("values", [])[:4]:
                observations.append(
                    f"Metric {item.get('name')}: {item.get('before')} -> {item.get('current')} {item.get('unit', '')}."
                )
        elif tool_name == "search_logs":
            for item in result.get("matches", [])[:3]:
                observations.append(
                    f"Log {item.get('level', '')} {item.get('timestamp', '')}: {item.get('message', '')}."
                )
        elif tool_name == "search_runbooks":
            for item in result.get("matches", [])[:2]:
                observations.append(
                    f"Runbook match {item.get('id')}: {item.get('name')} (score {item.get('match_score')})."
                )
        return observations

    @staticmethod
    def _hypothesis_from_context(
        context: dict[str, Any],
        observations: list[str],
    ) -> str:
        incident = context.get("incident", {}) or {}
        text = " ".join(
            [
                str(incident.get("title", "")),
                str(incident.get("description", "")),
                " ".join(observations),
            ]
        ).lower()

        mappings = [
            (("connection pool", "too many clients"), "Database connection-pool exhaustion is the leading hypothesis."),
            (("replica", "wal", "lag"), "Database replication lag is the leading hypothesis."),
            (("deadlock", "lock wait"), "Database transaction deadlock/lock-order regression is the leading hypothesis."),
            (("crashloopbackoff", "connection refused to config"), "Configuration rollout regression is the leading hypothesis."),
            (("oomkilled", "exit code 137"), "Memory exhaustion after the model/application change is the leading hypothesis."),
            (("cpu thrott", "98", "p99"), "CPU saturation or throttling is the leading hypothesis."),
            (("disk high watermark", "read-only"), "Storage exhaustion is the leading hypothesis."),
            (("dns", "no such host", "lookup timeout"), "DNS capacity or resolution failure is the leading hypothesis."),
            (("certificate", "x509", "tls handshake"), "Certificate expiry/renewal failure is the leading hypothesis."),
            (("no healthy upstream", "healthy targets"), "Load-balancer health-check or target-health failure is the leading hypothesis."),
            (("jwt", "jwks", "signature verification"), "Signing-key rotation/JWKS cache mismatch is the leading hypothesis."),
            (("payment", "provider", "timeout"), "External payment-provider latency/outage is the leading hypothesis."),
            (("event source mapping", "backlog"), "Disabled event-source consumption is the leading hypothesis."),
            (("concurrency", "queue", "backlog"), "Insufficient consumer concurrency is the leading hypothesis."),
            (("redis", "connection refused"), "Redis/session-cache outage is the leading hypothesis."),
            (("rate-limit", "429", "waf"), "WAF/rate-limit configuration regression is the leading hypothesis."),
            (("secret rotation", "invalid password"), "Credential/secret rotation regression is the leading hypothesis."),
            (("vendor", "third party", "timeout"), "Third-party dependency outage is the leading hypothesis."),
            (("release", "deployment", "5xx"), "Recent deployment regression is the leading hypothesis."),
        ]
        for terms, hypothesis in mappings:
            if sum(1 for term in terms if term in text) >= min(2, len(terms)):
                return hypothesis
        return "The available evidence indicates a service or dependency failure, but the specific cause is not yet confirmed."

    def deterministic(
        self,
        context: dict[str, Any],
        *,
        execution_mode: str = "mock",
        on_tool_execution: ToolObserver | None = None,
    ) -> tuple[InvestigationResult, list[InvestigationToolRun]]:
        observations: list[str] = []
        tool_runs: list[InvestigationToolRun] = []
        tools_used: list[str] = []

        for sequence, (tool_name, arguments) in enumerate(self._mock_plan(context), start=1):
            started = time.monotonic()
            try:
                result = execute_tool(tool_name, arguments)
                status = "success"
                error_message = ""
                tools_used.append(tool_name)
                observations.extend(self._summarize_tool_result(tool_name, result))
            except ToolRegistryError as exc:
                result = {"error": str(exc)}
                status = "failed"
                error_message = str(exc)

            tool_runs.append(
                InvestigationToolRun(
                    sequence=sequence,
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result,
                    status=status,
                    latency_ms=max(1, int((time.monotonic() - started) * 1000)),
                    execution_mode=execution_mode,
                    error_message=error_message,
                )
            )
            if on_tool_execution is not None:
                on_tool_execution(tool_runs[-1])

        successful = [item for item in tool_runs if item.status == "success"]
        evidence_found = any(
            item.result.get("found", True)
            and (
                item.result.get("values")
                or item.result.get("matches")
                or item.result.get("deployments")
            )
            for item in successful
        )
        missing = []
        if not evidence_found:
            missing.append("No matching local operational evidence was available.")
        if not any(item.tool_name == "get_recent_deployments" for item in successful):
            missing.append("Recent deployment/configuration evidence was not inspected in this pass.")

        hypothesis = self._hypothesis_from_context(context, observations)
        confidence = 0.78 if evidence_found and len(successful) >= 2 else 0.55 if successful else 0.35

        return (
            InvestigationResult(
                observations=observations[:10],
                tools_used=list(dict.fromkeys(tools_used)),
                leading_hypothesis=hypothesis,
                supporting_evidence=observations[:6],
                missing_evidence=missing,
                confidence=confidence,
            ),
            tool_runs,
        )

    def _fallback(
        self,
        context: dict[str, Any],
        *,
        started: float,
        error_message: str,
        existing_tool_runs: list[InvestigationToolRun] | None = None,
        retry_count: int = 0,
        on_tool_execution: ToolObserver | None = None,
    ) -> InvestigationRun:
        combined = list(existing_tool_runs or [])
        if combined:
            observations: list[str] = []
            for item in combined:
                if item.status == "success":
                    observations.extend(self._summarize_tool_result(item.tool_name, item.result))
            successful = [item for item in combined if item.status == "success"]
            output = InvestigationResult(
                observations=observations[:10],
                tools_used=list(dict.fromkeys(item.tool_name for item in successful)),
                leading_hypothesis=self._hypothesis_from_context(context, observations),
                supporting_evidence=observations[:6],
                missing_evidence=[
                    "Live investigation ended before final synthesis; fallback used only the evidence already collected."
                ],
                confidence=0.68 if len(successful) >= 2 else 0.5 if successful else 0.3,
            )
        else:
            output, combined = self.deterministic(
                context,
                execution_mode="fallback",
                on_tool_execution=on_tool_execution,
            )
        return InvestigationRun(
            output=output,
            model_name="deterministic-investigation-fallback-v1",
            latency_ms=max(1, int((time.monotonic() - started) * 1000)),
            retry_count=max(1, retry_count),
            execution_mode="fallback",
            error_message=error_message,
            tool_executions=combined,
        )

    def run(
        self,
        context: dict[str, Any],
        *,
        on_tool_execution: ToolObserver | None = None,
    ) -> InvestigationRun:
        started = time.monotonic()

        if settings.AI_MODE != "live":
            output, tool_runs = self.deterministic(
                context,
                execution_mode="mock",
                on_tool_execution=on_tool_execution,
            )
            return InvestigationRun(
                output=output,
                model_name="deterministic-investigation-v1",
                latency_ms=max(1, int((time.monotonic() - started) * 1000)),
                retry_count=0,
                execution_mode="mock",
                tool_executions=tool_runs,
            )

        if not settings.AI_API_KEY:
            return self._fallback(
                context,
                started=started,
                error_message="AI_MODE is live but AI_API_KEY is not configured.",
                on_tool_execution=on_tool_execution,
            )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": INVESTIGATION_SYSTEM},
            {"role": "user", "content": self.build_prompt(context)},
        ]
        tool_runs: list[InvestigationToolRun] = []
        successful_names: list[str] = []
        retry_count = 0
        model_name = ""
        total_provider_latency = 0
        budget = self._tool_budget()
        correction_sent = False

        try:
            provider = OpenAICompatibleProvider()

            # A bounded number of model turns prevents accidental loops even if a
            # provider/model behaves unexpectedly. One extra turn permits final synthesis.
            for _round in range(budget + 3):
                allow_tools = len(tool_runs) < budget
                turn = provider.complete_tool_turn(
                    messages=messages,
                    tools=tool_specs() if allow_tools else None,
                )
                retry_count += turn.retry_count
                total_provider_latency += turn.latency_ms
                model_name = turn.model_name

                if turn.tool_calls and allow_tools:
                    messages.append(turn.assistant_message)
                    for requested in turn.tool_calls:
                        if len(tool_runs) >= budget:
                            break
                        sequence = len(tool_runs) + 1
                        arguments = self._safe_arguments(requested.arguments)
                        tool_started = time.monotonic()
                        try:
                            result = execute_tool(requested.name, requested.arguments)
                            status = "success"
                            error_message = ""
                            successful_names.append(requested.name)
                        except (ToolRegistryError, ToolExecutionError) as exc:
                            result = {"error": str(exc)}
                            status = "failed"
                            error_message = str(exc)

                        tool_runs.append(
                            InvestigationToolRun(
                                sequence=sequence,
                                tool_name=requested.name,
                                arguments=arguments,
                                result=result,
                                status=status,
                                latency_ms=max(1, int((time.monotonic() - tool_started) * 1000)),
                                execution_mode="live",
                                error_message=error_message,
                            )
                        )
                        if on_tool_execution is not None:
                            on_tool_execution(tool_runs[-1])
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": requested.id,
                                "content": json.dumps(result, default=str)[:6000],
                            }
                        )

                    if len(tool_runs) >= budget:
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "The investigation tool budget is exhausted. "
                                    "Do not request more tools. Return the final JSON object now."
                                ),
                            }
                        )
                    continue

                if not tool_runs and not correction_sent:
                    correction_sent = True
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "You must inspect at least one read-only investigation tool "
                                "before finalizing. Select the most useful tool now."
                            ),
                        }
                    )
                    continue

                raw = extract_json_object(turn.content)
                try:
                    output = InvestigationResult.model_validate(raw)
                except ValidationError as validation_exc:
                    # The evidence-gathering phase succeeded, so give the model one
                    # bounded chance to repair only the final JSON shape. No tools are
                    # exposed on this repair turn, which prevents extra hidden actions.
                    messages.append(turn.assistant_message)
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Your final JSON did not match the InvestigationResult schema. "
                                "Repair the same answer without adding new evidence or tool calls. "
                                "Return JSON only with: observations=array[string], "
                                "tools_used=array[string], leading_hypothesis=string, "
                                "supporting_evidence=array[string], "
                                "missing_evidence=array[string], confidence=number 0..1. "
                                f"Validation error: {str(validation_exc)[:900]}"
                            ),
                        }
                    )
                    repair_turn = provider.complete_tool_turn(
                        messages=messages,
                        tools=None,
                    )
                    retry_count += repair_turn.retry_count
                    total_provider_latency += repair_turn.latency_ms
                    model_name = repair_turn.model_name
                    if repair_turn.tool_calls:
                        raise ProviderError(
                            "Investigation final-schema repair unexpectedly requested a tool."
                        )
                    repaired_raw = extract_json_object(repair_turn.content)
                    output = InvestigationResult.model_validate(repaired_raw)

                # Never trust a model-authored audit list over what was actually executed.
                output.tools_used = list(dict.fromkeys(successful_names))
                return InvestigationRun(
                    output=output,
                    model_name=model_name,
                    latency_ms=max(
                        total_provider_latency,
                        int((time.monotonic() - started) * 1000),
                    ),
                    retry_count=retry_count,
                    execution_mode="live",
                    tool_executions=tool_runs,
                )

            raise ProviderError("Investigation agent exceeded its bounded model-turn limit.")

        except (ProviderError, ValidationError, ValueError) as exc:
            return self._fallback(
                context,
                started=started,
                error_message=str(exc),
                existing_tool_runs=tool_runs,
                retry_count=retry_count,
                on_tool_execution=on_tool_execution,
            )
