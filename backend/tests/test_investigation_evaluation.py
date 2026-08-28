from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


def test_mock_investigation_evaluation_writes_structured_report(tmp_path):
    output = tmp_path / "investigation-evaluation.json"
    stdout = StringIO()

    call_command(
        "evaluate_investigation",
        mode="mock",
        limit=20,
        output=str(output),
        stdout=stdout,
    )

    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["mode_requested"] == "mock"
    assert report["scenario_count"] == 20
    assert report["execution_mode_counts"] == {"mock": 20}
    assert report["errors"] == []
    assert len(report["scenarios"]) == 20

    metrics = report["metrics"]
    assert metrics["completed_run_rate"] == 1.0
    assert metrics["fallback_rate"] == 0.0
    assert metrics["runs_with_tool_call_rate"] == 1.0
    assert metrics["successful_tool_call_rate"] == 1.0
    assert metrics["evidence_bearing_tool_call_rate"] == 1.0
    assert metrics["budget_compliance_rate"] == 1.0
    assert metrics["hypothesis_present_rate"] == 1.0
    assert metrics["mean_core_evidence_channel_coverage"] == 1.0
    assert metrics["full_core_evidence_channel_coverage_rate"] == 1.0
    assert metrics["deployment_inspection_recall"] == 1.0

    for scenario in report["scenarios"]:
        assert scenario["completed"] is True
        assert scenario["execution_mode"] == "mock"
        assert 1 <= scenario["tool_call_count"] <= report["tool_budget"]
        assert scenario["hypothesis_present"] is True
        assert 0.0 <= scenario["confidence"] <= 1.0


def test_investigation_evaluation_rejects_invalid_limit():
    with pytest.raises(CommandError, match="between 1 and 20"):
        call_command(
            "evaluate_investigation",
            mode="mock",
            limit=0,
            stdout=StringIO(),
        )


def test_investigation_evaluation_supports_targeted_slugs(tmp_path):
    output = tmp_path / "targeted-evaluation.json"

    call_command(
        "evaluate_investigation",
        mode="mock",
        slug=[
            "db-pool-exhaustion",
            "deployment-regression",
            "third-party-outage",
        ],
        output=str(output),
        stdout=StringIO(),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["scenario_count"] == 3
    assert [row["slug"] for row in report["scenarios"]] == [
        "db-pool-exhaustion",
        "deployment-regression",
        "third-party-outage",
    ]


def test_investigation_evaluation_rejects_unknown_slug():
    with pytest.raises(CommandError, match="Unknown --slug"):
        call_command(
            "evaluate_investigation",
            mode="mock",
            slug=["does-not-exist"],
            stdout=StringIO(),
        )


def test_mock_evaluation_report_keeps_human_auditable_outputs(tmp_path):
    output = tmp_path / "auditable-evaluation.json"

    call_command(
        "evaluate_investigation",
        mode="mock",
        slug=["deployment-regression"],
        output=str(output),
        stdout=StringIO(),
    )

    row = json.loads(output.read_text(encoding="utf-8"))["scenarios"][0]
    assert row["leading_hypothesis"]
    assert row["observations"]
    assert row["supporting_evidence"]
    assert isinstance(row["missing_evidence"], list)
