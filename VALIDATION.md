# Validation record

This is a new standalone repository. The earlier `thanos07/triageiq` repository was not modified.

## Checks completed in the build environment

- Compiled every backend Python source file with `compileall`.
- Added a migration-state correction matching Django 5.2.16 inherited `groups` and `is_active` field definitions.
- Pinned Django to exactly 5.2.16 so CI cannot silently install a different patch release.
- Parsed the changed TypeScript/TSX files with the TypeScript compiler; no syntax diagnostics were found.
- Loaded and structurally validated exactly 30 runbook knowledge cases.
- Loaded exactly 20 synthetic demo incident conditions.
- Executed the pure retrieval engine for all 20 conditions and confirmed every condition matched its declared runbook ID.
- Executed the deterministic Runbook Agent for all 20 conditions and validated the expanded Pydantic output, minimum step count, matched case, problem summary, and rollback guidance.
- Verified every runbook case has at least four keywords, three diagnostic steps, three solution steps, two verification steps, rollback guidance, escalation triggers, a caution, and required evidence.
- Executed temporary extraction against structured JSON, LOG text with a credential-like value, and a generated text PDF in the previous update.
- Retained information-gap propagation into the Runbook Agent.
- Added a searchable Runbook Library endpoint and page.
- Confirmed R2 credentials are backend-only placeholders and no Git history or remote is included.
- Confirmed Streamlit, FastAPI, Celery, Redis, Render, and paid storage dependencies were not introduced.

## Checks that require dependency installation

The execution environment cannot access the Python or npm package registries, so Django itself is unavailable here. Therefore, the complete Django database test suite and the full Next.js production build could not be executed in this environment. Run:

```bash
cd backend
python -m venv .venv
# activate the environment
pip install -r requirements-dev.txt
python manage.py makemigrations --check --dry-run
python manage.py migrate
pytest
python manage.py seed_demo

cd ../frontend
npm install
npm run typecheck
npm run build
```

After `seed_demo`, confirm the dashboard contains 20 synthetic incidents and `/runbooks` displays 30 cases.

## Cloudflare R2 verification

Before deployment:

1. Create a private R2 bucket.
2. Configure the two prefix lifecycle rules in `docs/temporary-uploads.md`.
3. Set `TEMP_UPLOAD_STORAGE_MODE=r2` and the four `R2_*` variables.
4. Upload one 7-day and one 10-day sample file.
5. Confirm the object keys use the matching prefixes.
6. Confirm re-extraction works before `expires_at`.
7. Confirm the API refuses re-extraction after `expires_at` even if physical R2 deletion has not completed yet.
