# TriageIQ Django AI

A clean-room rebuild of TriageIQ as a **Django-first AI incident-management application** with a modern Next.js interface. This repository is independent from the earlier Streamlit/FastAPI project and is designed to demonstrate Django, REST APIs, PostgreSQL, AI agents, human-in-the-loop workflows, and production-minded deployment.

## What the application does

```text
Incident submitted
      ↓
Deterministic normalization
      ↓
Severity Agent
      ↓
Investigation Agent
      ↓
Root-Cause Agent
      ↓
Runbook Agent
      ↓
Communication Agent
      ↓
Human review
      ↓
Remediation actions
      ↓
Verified resolution
      ↓
Draft / final PDF report
```

The AI is advisory. A human reviewer approves the plan, and an operator must record actual actions and recovery evidence before the incident can be resolved.

## Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 LTS, Django REST Framework |
| Authentication | JWT with Simple JWT and role-based permissions |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |
| Database | SQLite locally; Neon PostgreSQL in deployment |
| AI | OpenAI-compatible provider; Groq + `openai/gpt-oss-20b` by default |
| Reliability | Deterministic demo/fallback mode, staged resumable execution |
| Temporary files | Private Cloudflare R2 with 7/10-day lifecycle expiry; local mode for development |
| Extraction | PyPDF, JSON/CSV parsers, text/log preprocessing and secret redaction |
| Reporting | ReportLab PDF generation in memory |
| API docs | OpenAPI / Swagger through drf-spectacular |
| Testing | Pytest + pytest-django |

## Major features

- Warm cream, camel, sand, taupe, and espresso visual system
- User roles: Administrator, Incident Manager, Reviewer, Viewer
- Searchable incident registry and operational dashboard
- Recoverable, one-stage-per-request AI pipeline
- Five visible and auditable AI agents, including a bounded Investigation Agent
- Read-only local Investigation tools for deployments, service metrics, logs, and runbook search
- Per-tool audit records with arguments, sanitized results, latency, status, and live/mock/fallback mode
- Searchable 30-case operational Runbook Library with transparent retrieval
- Provider abstraction for Groq or another OpenAI-compatible endpoint
- GPT-OSS model configuration through environment variables
- Deterministic mock mode that works without an API key
- Human approval, rejection, revision request, and severity override
- Actual remediation actions and verification evidence
- Reopen and close lifecycle support
- Complete status and agent execution timeline
- PDF, JSON, CSV, TXT, and LOG extraction with an editable confirmation preview
- Private 7/10-day source retention using Cloudflare R2 lifecycle rules
- Missing-source information converted into actionable runbook collection steps
- Draft AI triage PDF before resolution
- Final incident resolution PDF after verification
- Seeded demo account and 20 realistic synthetic incident conditions
- Django Admin for internal administration
- Swagger API documentation and health endpoint

## Repository structure

```text
triageiq-django-ai/
├── backend/
│   ├── accounts/              # Custom user and roles
│   ├── ai_engine/             # Provider, schemas, prompts, five agents, tools, pipeline
│   ├── incidents/             # Models, uploads, extraction, lifecycle, review and resolution
│   ├── reports/               # Branded PDF generation
│   ├── config/                # Django settings and routing
│   ├── tests/                 # End-to-end backend workflow tests
│   ├── api/index.py           # Vercel Python entrypoint
│   └── manage.py
├── frontend/
│   ├── app/                   # Next.js App Router pages
│   ├── components/            # Reusable modern UI components
│   └── lib/                   # API client, types, auth and status helpers
├── docs/
└── .github/workflows/ci.yml
```

## Local setup

### 1. Backend

Python 3.12 or newer is recommended.

```bash
cd backend
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install and initialise:

```bash
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Sample upload files are available in `backend/sample_data/`.

Backend URLs:

- API: `http://localhost:8000/api/`
- Swagger: `http://localhost:8000/api/docs/`
- Django Admin: `http://localhost:8000/admin/`
- Health: `http://localhost:8000/api/health/`

Seeded account:

```text
Email: demo@triageiq.dev
Password: DemoPass123!
```

Change the password through environment variables or Django Admin before any public deployment.

### 2. Frontend

Open a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## AI modes

### Free deterministic demo mode

This is the default and requires no key:

```env
AI_MODE=mock
```

It creates structured, realistic agent outputs and keeps the interviewer demo reliable even when quota is unavailable.

### Live GPT-OSS mode through Groq

```env
AI_MODE=live
AI_PROVIDER=groq
AI_BASE_URL=https://api.groq.com/openai/v1
AI_API_KEY=your_key
AI_MODEL=openai/gpt-oss-20b
AI_FALLBACK_MODEL=openai/gpt-oss-120b
AI_INVESTIGATION_MAX_TOOL_CALLS=3
```

The Investigation Agent uses bounded local function calling. The configured tool-call budget defaults to 3 and is clamped to 1-5 calls. The model may stop early when it has enough evidence.

Execution modes are explicit:

- `live`: the configured model selects read-only tools and produces the final structured investigation;
- `mock`: deterministic local behavior for repeatable demos and tests;
- `fallback`: live execution was expected but provider, quota, validation, or another live-path failure required safe deterministic fallback.

The provider uses the OpenAI Python client against an OpenAI-compatible base URL, so another compatible provider can be adopted without rewriting the agents.

## Why the pipeline is staged

The frontend does not send one long request for all agents. It calls the next incomplete stage repeatedly:

```text
Normalization → Severity → Investigation → Root Cause → Runbook → Summary
```

Each Investigation tool request is validated against an explicit registry, executed locally, sanitized, and recorded in the audit trail before the workflow continues.

```text
POST /api/incidents/{id}/advance/
```

Each request performs one stage and saves its result. This design:

- fits free serverless function limits more reliably;
- resumes after a failed request or browser refresh;
- avoids Celery, Redis, and paid workers in version one;
- makes every agent visible in the interface and audit trail;
- allows the architecture to move to Celery later without rewriting agent logic.

## Main API endpoints

```text
POST /api/auth/token/
POST /api/auth/refresh/
GET  /api/auth/me/
GET  /api/dashboard/
GET  /api/runbooks/
GET  /api/incidents/
POST /api/incidents/
POST /api/incidents/extract-upload/
GET  /api/incidents/{id}/
POST /api/incidents/{id}/advance/
POST /api/incidents/{id}/source-file/reextract/
POST /api/incidents/{id}/source-file/delete/
POST /api/incidents/{id}/review/
POST /api/incidents/{id}/start-resolution/
POST /api/incidents/{id}/resolve/
POST /api/incidents/{id}/reopen/
POST /api/incidents/{id}/close/
GET  /api/incidents/{id}/report/?draft=true
GET  /api/incidents/{id}/report/
POST /api/incidents/demo/
```

## Temporary source-document extraction

The New Incident screen supports manual entry or temporary source upload. Supported formats are PDF, JSON, CSV, TXT, and LOG. The user chooses 7- or 10-day retention, reviews an editable extraction preview, and then confirms the incident.

The original file is stored privately in Cloudflare R2 and automatically expires through prefix-based lifecycle rules. No Render service, cron request, Redis, or Celery worker is required. The structured incident data remains in Neon after the original expires.

Local development uses `backend/.temporary-uploads`. Deployment variables and lifecycle rules are documented in [`docs/temporary-uploads.md`](docs/temporary-uploads.md).

Missing fields are stored as structured information gaps and passed to the root-cause and runbook agents. The runbook explains how to collect the absent evidence instead of inventing it.

## PDF reports

PDFs are generated in memory and returned directly to the browser. No paid object storage is required.

Draft report:

```text
GET /api/incidents/{id}/report/?draft=true
```

Final report, available only after resolution or closure:

```text
GET /api/incidents/{id}/report/
```

The final report includes the original incident, all agent results, confidence and model information, human decisions, actual actions, verified root cause, status timeline, and final outcome.

## Synthetic conditions and runbook coverage

`python manage.py seed_demo` creates exactly **20 synthetic incident conditions**. All 20 complete the five-agent pipeline and are distributed across awaiting review, revision required, rejected, remediation in progress, and resolved states. Each scenario records its expected runbook case.

The Runbook Library contains exactly **30 problem–diagnosis–solution cases** covering databases, Kubernetes, capacity, networking, certificates, authentication, payments, queues, caching, edge controls, deployment, configuration, third-party providers, storage, data integrity, security, observability, scheduled jobs, and unknown incidents. See [`docs/runbook-library.md`](docs/runbook-library.md).

The parameterised test suite contributes:

- 20 independent synthetic incident-to-runbook matching conditions;
- 30 independent runbook completeness conditions;
- count, fallback, seed-command, lifecycle, upload, authentication, and PDF conditions.

## Investigation Agent evaluation

The repository includes a database-free evaluation command for the Investigation Agent:

```bash
cd backend
python manage.py evaluate_investigation --mode mock
```

It measures tool execution reliability, evidence-bearing calls, bounded-call compliance, synthetic evidence-channel coverage, deployment-inspection recall, latency, and output completeness. These metrics **do not claim semantic root-cause accuracy**.

Deterministic 20-scenario benchmark:

| Metric | Result |
|---|---:|
| Scenarios completed | 20 / 20 |
| Successful tool-call rate | 100.0% |
| Evidence-bearing tool-call rate | 100.0% |
| Full core-evidence coverage | 100.0% |
| Deployment inspection recall | 100.0% |
| Fallback rate | 0.0% |
| Mean tool calls | 3.00 |
| Mean confidence | 0.780 |

A targeted live Groq sample was also run across three qualitatively different scenarios: database pool exhaustion, deployment regression, and a third-party outage.

| Metric | Result |
|---|---:|
| Scenarios completed in live mode | 3 / 3 |
| Successful tool-call rate | 100.0% |
| Evidence-bearing tool-call rate | 77.8% |
| Full core-evidence coverage | 100.0% |
| Deployment inspection recall | 100.0% |
| Fallback rate | 0.0% |
| Mean tool calls | 3.00 |
| Mean confidence | 0.850 |

The live sample is intentionally small and is not presented as an accuracy benchmark. Two successful deployment lookups returned no deployment evidence, which is preserved in the reported 77.8% evidence-bearing rate rather than hidden.

Targeted live or mock scenarios can be selected by repeating `--slug`:

```bash
python manage.py evaluate_investigation \
  --mode live \
  --slug db-pool-exhaustion \
  --slug deployment-regression \
  --slug third-party-outage
```

## Tests

```bash
cd backend
pytest
```

The tests include the end-to-end lifecycle and PDF flow, temporary upload propagation, authentication, 20 synthetic mapping conditions, 30 runbook completeness conditions, unknown-case fallback, and verification that the seed command creates exactly 20 usable incidents.

## Free deployment plan

### Frontend: Vercel

Create a Vercel project with `frontend` as the root directory and set:

```env
NEXT_PUBLIC_API_URL=https://your-backend-domain/api
```

### Backend: Vercel for the first portfolio release

Create a second Vercel project with `backend` as the root directory. Add all variables from `backend/.env.example`, using production values.

Use a pooled Neon connection string:

```env
DATABASE_URL=postgresql://...
```

Run migrations against Neon from your local machine before the first deployment:

```bash
cd backend
DATABASE_URL="your-neon-url" python manage.py migrate
DATABASE_URL="your-neon-url" python manage.py seed_demo
```

Do not use SQLite in deployed serverless functions.

### Upgrade path

When persistent background workers become necessary, retain Vercel for Next.js and move Django plus Celery to an always-on VM. The current service layer is already separated so that the staged functions can later become Celery tasks.

## Portfolio talking points

- Designed a Django domain model for a real incident lifecycle rather than a single AI form.
- Implemented role-based access and human accountability around AI recommendations.
- Used typed structured outputs for five specialised agents.
- Built a bounded Investigation Agent with model-selected local tools, schema validation, explicit audit records, and deterministic fallback behavior.
- Added reproducible mock evaluation plus a transparent targeted live-provider sample.
- Built provider-independent AI integration and deterministic fallback behaviour.
- Designed a resumable workflow for free serverless infrastructure constraints.
- Generated audit-ready PDF reports without permanent report storage.
- Added private, automatically expiring source-document retention and secure extraction.
- Converted incomplete uploaded evidence into explicit agent information-gap handling.
- Created a responsive custom design system instead of relying on Streamlit.

## Security notes

- Never commit `.env` files or API keys.
- Replace the demo credentials in public deployments.
- Keep CORS origins restricted to the deployed frontend.
- AI output is advisory and cannot directly resolve an incident.
- Destructive operational actions should remain behind organisation-specific approvals.

## License

MIT
