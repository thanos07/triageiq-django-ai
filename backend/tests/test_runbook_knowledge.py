from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.core.management import call_command

from ai_engine.runbook_knowledge import load_runbook_cases, retrieve_runbook_cases
from incidents.models import Incident

_DATA_DIR = Path(__file__).resolve().parents[1] / "ai_engine" / "data"
DEMO_CONDITIONS = json.loads((_DATA_DIR / "demo_incidents.json").read_text(encoding="utf-8"))
RUNBOOK_CASES = json.loads((_DATA_DIR / "runbook_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "condition",
    DEMO_CONDITIONS,
    ids=[item["slug"] for item in DEMO_CONDITIONS],
)
def test_each_of_20_synthetic_conditions_matches_expected_runbook(condition):
    matches = retrieve_runbook_cases(
        {
            "incident": condition,
            "severity": {"category": ""},
            "root_cause": {},
        },
        limit=3,
    )
    assert matches
    assert matches[0]["id"] == condition["expected_runbook_id"]
    assert matches[0]["match_score"] > 0


@pytest.mark.parametrize(
    "case",
    RUNBOOK_CASES,
    ids=[item["id"] for item in RUNBOOK_CASES],
)
def test_each_of_30_runbook_cases_has_problem_diagnosis_solution_and_safety(case):
    assert case["problem"].strip()
    assert len(case["keywords"]) >= 4
    assert len(case["diagnostic_steps"]) >= 3
    assert len(case["solution_steps"]) >= 3
    assert len(case["verification_steps"]) >= 2
    assert case["rollback_plan"]
    assert case["escalation_triggers"]
    assert case["caution"].strip()
    assert case["missing_information"]


def test_knowledge_base_counts_are_intentional():
    assert len(DEMO_CONDITIONS) == 20
    assert len(RUNBOOK_CASES) == 30
    assert len(load_runbook_cases()) == 30
    assert len({item["expected_runbook_id"] for item in DEMO_CONDITIONS}) == 20
    assert len({item["id"] for item in RUNBOOK_CASES}) == 30


def test_unknown_incident_uses_general_safety_runbook():
    match = retrieve_runbook_cases(
        {"incident": {"title": "Unexplained behaviour", "description": "No telemetry is available."}},
        limit=1,
    )[0]
    assert match["id"] == "rb-030"


@pytest.mark.django_db
def test_seed_demo_creates_exactly_20_synthetic_incidents():
    call_command("seed_demo")
    incidents = Incident.objects.filter(source="synthetic-seed")
    assert incidents.count() == 20
    assert incidents.filter(status=Incident.Status.RESOLVED).count() == 6
    assert incidents.filter(status=Incident.Status.REMEDIATION_IN_PROGRESS).count() == 3
    assert incidents.filter(status=Incident.Status.REVISION_REQUIRED).count() == 2
    assert incidents.filter(status=Incident.Status.REJECTED).count() == 1
    assert incidents.filter(status=Incident.Status.AWAITING_REVIEW).count() == 8
    for incident in incidents.select_related("workflow"):
        expected = incident.raw_input["expected_runbook_id"]
        assert incident.workflow.runbook_output["matched_case_id"] == expected
