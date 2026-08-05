# Architecture

## Runtime topology

```text
Browser
  │
  ▼
Next.js UI on Vercel
  │ JWT + REST
  ▼
Django REST API
  ├── Accounts and role permissions
  ├── Incident lifecycle service
  ├── Staged AI orchestration
  ├── Human review service
  ├── Resolution records
  ├── Audit timeline
  ├── Temporary source extraction
  └── PDF generation
  │
  ├──────────────► Groq/OpenAI-compatible API
  ├──────────────► Private Cloudflare R2 (7/10-day source retention)
  │
  ▼
Neon PostgreSQL
```

## Domain model

- `User`: email login and role.
- `Incident`: source facts and lifecycle state.
- `WorkflowResult`: latest structured output from every stage.
- `AgentExecution`: immutable model, latency, confidence, mode, error, and output record.
- `ReviewDecision`: reviewer action, note, and optional override.
- `ResolutionRecord`: final verified cause and recovery evidence.
- `ResolutionAction`: each action actually performed.
- `StatusEvent`: full incident state history.
- `TemporaryIncidentFile`: private object metadata, extracted fields, information gaps, and expiry state.

## Lifecycle

```text
submitted → triaging → awaiting_review
                           ├─ approved → remediation_in_progress → resolved → closed
                           ├─ revision_required → triaging
                           └─ rejected
resolved/closed → reopened → triaging
triaging → failed → triaging
```

All transitions pass through `incidents.services.lifecycle.transition_incident`. Arbitrary state edits are not exposed through the REST API.

## Agent boundaries

Each agent owns one structured output contract:

1. Severity: level, urgency, category, signals, confidence.
2. Root cause: probable cause, evidence, alternatives, missing information, confidence.
3. Runbook: safe steps, verification, risk, escalation, rollback, confidence.
4. Communication: technical, executive and customer-safe summaries.

Pydantic validates live model responses. Invalid or unavailable model responses automatically use deterministic fallback output and remain visible in the audit record.

## Serverless resilience

`advance_pipeline` performs one stage per request and stores the result before the next request. `WorkflowResult.is_processing` prevents overlapping stage execution. This avoids a mandatory queue in the first free deployment while still providing resumability.

## Temporary source workflow

```text
PDF / JSON / CSV / TXT / LOG
        ↓
Django validates and extracts synchronously
        ↓
Private object written under a 7-day or 10-day R2 prefix
        ↓
User edits and confirms extracted incident facts
        ↓
TemporaryIncidentFile linked to Incident
        ↓
Information gaps passed to root-cause and runbook agents
        ↓
R2 lifecycle deletes the original automatically
```

The binary file is never stored in PostgreSQL. Re-extraction reads the private object but preserves any fields already edited by a human. Application expiry is enforced from `expires_at`, even if physical R2 deletion completes later.


## Runbook knowledge retrieval

The Runbook Agent uses a checked-in 30-case operational knowledge base. Direct incident evidence is scored more strongly than AI-derived root-cause context, preventing a weak root-cause guess from overpowering source symptoms. The agent returns the best case ID, name, problem summary, match score, related cases, required evidence, diagnostic steps, bounded mitigations, verification, rollback, escalation triggers, and safety caution.

The 20 seeded synthetic incidents each declare an expected case ID. Parameterised tests verify every mapping, while a second 30-case test validates the completeness of every knowledge entry.
