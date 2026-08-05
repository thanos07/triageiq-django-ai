# Runbook knowledge base

TriageIQ includes **30 curated problem–diagnosis–solution cases**. The Runbook Agent uses transparent keyword/category scoring to retrieve the closest cases, then combines the best match with incident-specific information gaps and human-safety guardrails.

The library is available in the UI at `/runbooks` and through `GET /api/runbooks/`.

| ID | Problem case | Category |
|---|---|---|
| `rb-001` | PostgreSQL connection-pool exhaustion | database |
| `rb-002` | Database replication lag | database |
| `rb-003` | Database deadlock or lock contention | database |
| `rb-004` | Kubernetes CrashLoopBackOff | kubernetes |
| `rb-005` | Container out-of-memory termination | capacity |
| `rb-006` | CPU saturation and request throttling | capacity |
| `rb-007` | Disk pressure or filesystem full | storage |
| `rb-008` | DNS resolution failure | network |
| `rb-009` | TLS certificate expiry or trust failure | security |
| `rb-010` | Authentication service outage | authentication |
| `rb-011` | JWT or token validation failure | authentication |
| `rb-012` | Payment gateway timeout | payments |
| `rb-013` | Webhook processing backlog | integration |
| `rb-014` | Message queue backlog or consumer lag | messaging |
| `rb-015` | Redis or cache outage | cache |
| `rb-016` | API rate-limit or WAF misconfiguration | edge |
| `rb-017` | Load balancer has no healthy upstream | network |
| `rb-018` | Application deployment regression | deployment |
| `rb-019` | Invalid configuration, secret, or feature flag | configuration |
| `rb-020` | Third-party dependency outage | third-party |
| `rb-021` | Network packet loss or connectivity degradation | network |
| `rb-022` | Object storage access failure | storage |
| `rb-023` | CDN outage or stale-cache incident | edge |
| `rb-024` | Email or notification delivery delay | notifications |
| `rb-025` | Data corruption or integrity mismatch | data-integrity |
| `rb-026` | Credential or secret exposure | security |
| `rb-027` | DDoS or abusive traffic spike | security |
| `rb-028` | Logging or observability pipeline failure | observability |
| `rb-029` | Scheduled job or cron failure | automation |
| `rb-030` | Unknown or insufficiently observed incident | unknown |

## What every case contains

- A concise operational problem definition
- Matching keywords and applicable severity levels
- At least three diagnostic steps
- At least three bounded solution steps
- At least two recovery-verification checks
- Required evidence and missing-information guidance
- Rollback guidance
- Escalation triggers
- A safety caution

## Retrieval behaviour

The deterministic demo mode ranks cases using the incident title, description, service, business impact, severity category, root-cause category, probable cause, and evidence. Long operational phrases score more strongly than generic one-word matches. The top case is included in the generated runbook as `matched_case_id` and `matched_case_name`; two related cases are retained for reviewer context.

Unknown or weakly observed incidents fall back to `rb-030`, which prioritises evidence collection, reversible stabilisation, and escalation rather than invented remediation.

## Synthetic coverage

The seed command creates 20 incident conditions. Each condition declares an expected runbook ID, and the test suite verifies all 20 mappings independently. A second 30-case parameterised test verifies that every runbook entry includes its required problem, diagnosis, solution, verification, rollback, escalation, safety, and evidence fields.
