from pydantic import BaseModel, Field


class SeverityResult(BaseModel):
    level: str
    urgency: str
    category: str
    confidence: float = Field(ge=0, le=1)
    rationale: str
    signals: list[str] = Field(default_factory=list)


class InvestigationResult(BaseModel):
    observations: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    leading_hypothesis: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class RootCauseResult(BaseModel):
    probable_cause: str
    category: str
    evidence: list[str] = Field(default_factory=list)
    alternative_causes: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class RunbookStep(BaseModel):
    order: int
    action: str
    rationale: str
    verification: str
    risk: str = "low"


class MissingInformation(BaseModel):
    field: str
    reason_required: str
    collection_method: str
    example_command: str | None = None
    blocks_resolution: bool = False
    fallback_action: str | None = None


class RunbookResult(BaseModel):
    title: str
    matched_case_id: str = ""
    matched_case_name: str = ""
    problem_summary: str = ""
    match_score: float = 0.0
    related_cases: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    steps: list[RunbookStep]
    missing_information: list[MissingInformation] = Field(default_factory=list)
    escalate: bool
    escalation_reason: str = ""
    rollback_plan: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class SummaryResult(BaseModel):
    technical_summary: str
    executive_summary: str
    customer_update: str
    business_impact: str
    next_update: str
    confidence: float = Field(ge=0, le=1)
