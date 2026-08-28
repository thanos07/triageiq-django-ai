from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test.utils import override_settings

from ai_engine.agents.investigation import InvestigationAgent
from ai_engine.tools.demo_evidence import get_service_record


_DATA_PATH = (
    Path(__file__).resolve().parents[3]
    / "ai_engine"
    / "data"
    / "demo_incidents.json"
)

_CORE_TOOL_BY_CHANNEL = {
    "metrics": "get_service_metrics",
    "logs": "search_logs",
    "deployments": "get_recent_deployments",
}


def _ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _mean(values: list[int | float]) -> float:
    return round(float(mean(values)), 4) if values else 0.0


def _p95(values: list[int | float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 4)


def _evidence_payload_present(result: dict[str, Any]) -> bool:
    if not result.get("found", True):
        return False
    return bool(
        result.get("values")
        or result.get("matches")
        or result.get("deployments")
    )


class Command(BaseCommand):
    help = (
        "Evaluate the Investigation Agent against the 20 synthetic demo "
        "incidents without mutating the database."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--mode",
            choices=("mock", "live"),
            default="mock",
            help="Agent execution mode. Defaults to mock.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Number of demo scenarios to evaluate (1-20).",
        )
        parser.add_argument(
            "--slug",
            action="append",
            default=[],
            help=(
                "Evaluate only the named demo scenario. Repeat --slug to "
                "select multiple scenarios. When supplied, --limit applies "
                "after slug filtering."
            ),
        )
        parser.add_argument(
            "--output",
            default="",
            help="Optional path for the JSON report.",
        )

    @staticmethod
    def _load_scenarios() -> list[dict[str, Any]]:
        with _DATA_PATH.open("r", encoding="utf-8") as handle:
            scenarios = json.load(handle)

        if not isinstance(scenarios, list) or len(scenarios) != 20:
            raise CommandError(
                "demo_incidents.json must contain exactly 20 scenarios."
            )
        return scenarios

    @staticmethod
    def _context(scenario: dict[str, Any]) -> dict[str, Any]:
        reported = str(scenario.get("reported_severity", "unknown"))
        urgency = "immediate" if reported in {"critical", "high"} else "standard"
        return {
            "incident": {
                "reference": f"EVAL-{str(scenario.get('slug', 'scenario')).upper()}",
                "title": scenario.get("title", ""),
                "description": scenario.get("description", ""),
                "service_name": scenario.get("service_name", ""),
                "environment": scenario.get("environment", ""),
                "reported_severity": reported,
                "business_impact": scenario.get("business_impact", ""),
                "extracted_context": {},
                "information_gaps": [],
            },
            "severity": {
                "level": reported,
                "urgency": urgency,
                "category": "availability",
                "confidence": 1.0,
                "rationale": "Synthetic evaluation context.",
                "signals": [scenario.get("title", "")],
            },
        }

    @staticmethod
    def _expected_core_tools(service_name: str) -> list[str]:
        profile = get_service_record(service_name) or {}
        expected = []
        for channel, tool_name in _CORE_TOOL_BY_CHANNEL.items():
            if profile.get(channel):
                expected.append(tool_name)
        return expected

    def handle(self, *args, **options) -> None:
        mode = str(options["mode"]).strip().lower()
        limit = int(options["limit"])
        output_path = str(options["output"]).strip()

        if not 1 <= limit <= 20:
            raise CommandError("--limit must be between 1 and 20.")

        if mode == "live" and not settings.AI_API_KEY:
            raise CommandError(
                "--mode live requires AI_API_KEY. The key is never written "
                "to the evaluation report."
            )

        scenarios = self._load_scenarios()
        requested_slugs = [
            str(value).strip()
            for value in options.get("slug", [])
            if str(value).strip()
        ]
        if requested_slugs:
            by_slug = {
                str(item.get("slug", "")): item
                for item in scenarios
            }
            missing = [
                slug for slug in requested_slugs
                if slug not in by_slug
            ]
            if missing:
                raise CommandError(
                    "Unknown --slug value(s): "
                    + ", ".join(missing)
                )
            scenarios = [by_slug[slug] for slug in requested_slugs]

        scenarios = scenarios[:limit]
        rows: list[dict[str, Any]] = []
        tool_usage: Counter[str] = Counter()
        execution_modes: Counter[str] = Counter()
        errors: list[dict[str, str]] = []

        with override_settings(AI_MODE=mode):
            for scenario in scenarios:
                slug = str(scenario.get("slug", "unknown"))
                service = str(scenario.get("service_name", ""))
                expected_tools = self._expected_core_tools(service)

                try:
                    run = InvestigationAgent().run(self._context(scenario))
                except Exception as exc:
                    errors.append({"slug": slug, "error": str(exc)})
                    rows.append(
                        {
                            "slug": slug,
                            "service_name": service,
                            "completed": False,
                            "error": str(exc),
                            "expected_core_tools": expected_tools,
                        }
                    )
                    continue

                execution_modes[run.execution_mode] += 1
                successful_runs = [
                    item for item in run.tool_executions if item.status == "success"
                ]
                successful_tools = [item.tool_name for item in successful_runs]
                tool_usage.update(successful_tools)

                expected_set = set(expected_tools)
                inspected_expected = expected_set.intersection(successful_tools)
                coverage = (
                    _ratio(len(inspected_expected), len(expected_set))
                    if expected_set
                    else 1.0
                )

                evidence_bearing_calls = sum(
                    1
                    for item in successful_runs
                    if _evidence_payload_present(item.result)
                )

                rows.append(
                    {
                        "slug": slug,
                        "service_name": service,
                        "completed": True,
                        "execution_mode": run.execution_mode,
                        "model_name": run.model_name,
                        "latency_ms": run.latency_ms,
                        "retry_count": run.retry_count,
                        "tool_call_count": len(run.tool_executions),
                        "successful_tool_call_count": len(successful_runs),
                        "evidence_bearing_tool_call_count": evidence_bearing_calls,
                        "successful_tools": successful_tools,
                        "expected_core_tools": expected_tools,
                        "core_evidence_channel_coverage": coverage,
                        "hypothesis_present": bool(run.output.leading_hypothesis.strip()),
                        "observation_count": len(run.output.observations),
                        "supporting_evidence_count": len(run.output.supporting_evidence),
                        "missing_evidence_count": len(run.output.missing_evidence),
                        "confidence": run.output.confidence,
                        "leading_hypothesis": run.output.leading_hypothesis,
                        "observations": run.output.observations,
                        "supporting_evidence": run.output.supporting_evidence,
                        "missing_evidence": run.output.missing_evidence,
                        "error_message": run.error_message,
                    }
                )

        completed = [row for row in rows if row.get("completed")]
        total_tool_calls = sum(int(row.get("tool_call_count", 0)) for row in completed)
        successful_tool_calls = sum(
            int(row.get("successful_tool_call_count", 0)) for row in completed
        )
        evidence_bearing_calls = sum(
            int(row.get("evidence_bearing_tool_call_count", 0)) for row in completed
        )

        deployment_expected = [
            row
            for row in completed
            if "get_recent_deployments" in row.get("expected_core_tools", [])
        ]
        deployment_inspected = sum(
            1
            for row in deployment_expected
            if "get_recent_deployments" in row.get("successful_tools", [])
        )

        tool_budget = InvestigationAgent._tool_budget()
        metrics = {
            "completed_run_rate": _ratio(len(completed), len(scenarios)),
            "fallback_rate": _ratio(execution_modes.get("fallback", 0), len(completed)),
            "runs_with_tool_call_rate": _ratio(
                sum(
                    1
                    for row in completed
                    if int(row.get("tool_call_count", 0)) >= 1
                ),
                len(completed),
            ),
            "successful_tool_call_rate": _ratio(successful_tool_calls, total_tool_calls),
            "evidence_bearing_tool_call_rate": _ratio(
                evidence_bearing_calls, successful_tool_calls
            ),
            "budget_compliance_rate": _ratio(
                sum(
                    1
                    for row in completed
                    if int(row.get("tool_call_count", 0)) <= tool_budget
                ),
                len(completed),
            ),
            "mean_core_evidence_channel_coverage": _mean(
                [float(row["core_evidence_channel_coverage"]) for row in completed]
            ),
            "full_core_evidence_channel_coverage_rate": _ratio(
                sum(
                    1
                    for row in completed
                    if float(row["core_evidence_channel_coverage"]) == 1.0
                ),
                len(completed),
            ),
            "deployment_inspection_recall": (
                _ratio(deployment_inspected, len(deployment_expected))
                if deployment_expected
                else None
            ),
            "hypothesis_present_rate": _ratio(
                sum(1 for row in completed if row.get("hypothesis_present")),
                len(completed),
            ),
            "mean_tool_calls": _mean(
                [int(row.get("tool_call_count", 0)) for row in completed]
            ),
            "mean_latency_ms": _mean(
                [int(row.get("latency_ms", 0)) for row in completed]
            ),
            "p95_latency_ms": _p95(
                [int(row.get("latency_ms", 0)) for row in completed]
            ),
            "mean_confidence": _mean(
                [float(row.get("confidence", 0)) for row in completed]
            ),
            "mean_observation_count": _mean(
                [int(row.get("observation_count", 0)) for row in completed]
            ),
            "mean_supporting_evidence_count": _mean(
                [int(row.get("supporting_evidence_count", 0)) for row in completed]
            ),
        }

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dataset": "ai_engine/data/demo_incidents.json",
            "mode_requested": mode,
            "scenario_count": len(scenarios),
            "tool_budget": tool_budget,
            "execution_mode_counts": dict(sorted(execution_modes.items())),
            "tool_usage": dict(sorted(tool_usage.items())),
            "metrics": metrics,
            "errors": errors,
            "scenarios": rows,
            "notes": [
                (
                    "Core evidence coverage measures whether the agent inspected "
                    "the synthetic metrics/log/deployment channels that actually "
                    "exist for each service. It is not a claim of root-cause accuracy."
                ),
                (
                    "Hypothesis presence checks output completeness only; this "
                    "benchmark does not label semantic hypothesis correctness."
                ),
                (
                    "Live-mode results depend on the configured provider/model "
                    "and may vary between runs."
                ),
            ],
        }

        if output_path:
            target = Path(output_path).expanduser()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            self.stdout.write(f"JSON report: {target}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Investigation evaluation complete: "
                f"{len(completed)}/{len(scenarios)} scenarios completed."
            )
        )
        self.stdout.write(f"Mode counts: {dict(sorted(execution_modes.items()))}")
        self.stdout.write(
            "Successful tool-call rate: "
            f"{metrics['successful_tool_call_rate']:.1%}"
        )
        self.stdout.write(
            "Evidence-bearing tool-call rate: "
            f"{metrics['evidence_bearing_tool_call_rate']:.1%}"
        )
        self.stdout.write(
            "Full core-evidence coverage: "
            f"{metrics['full_core_evidence_channel_coverage_rate']:.1%}"
        )
        deployment_metric = metrics["deployment_inspection_recall"]
        if deployment_metric is not None:
            self.stdout.write(
                "Deployment inspection recall: "
                f"{deployment_metric:.1%}"
            )
        self.stdout.write(f"Fallback rate: {metrics['fallback_rate']:.1%}")
        self.stdout.write(f"Mean tool calls: {metrics['mean_tool_calls']:.2f}")
        self.stdout.write(f"Mean confidence: {metrics['mean_confidence']:.3f}")
