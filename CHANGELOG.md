# Changelog

## 1.2.1 — Django migration consistency fix

- Pinned Django to `5.2.16` so local, CI, and deployment environments use the same patch release.
- Added `accounts/0002_sync_abstract_user_fields.py`.
- Aligned the inherited `groups` and `is_active` field state with Django 5.2.16.
- Prevented `python manage.py makemigrations --check --dry-run` from requesting an uncommitted migration.
- Preserved `0001_initial.py` rather than rewriting migration history.

## 1.2.0 — Synthetic conditions and runbook library

- Increased seeded demo incidents from 2 to exactly 20 synthetic operational conditions.
- Added expected runbook IDs and varied demo lifecycle states.
- Added a 30-case problem–diagnosis–solution runbook knowledge base.
- Added transparent keyword/category retrieval with top match and related cases.
- Added matched case, problem summary, required evidence, and match score to Runbook Agent output.
- Added a searchable authenticated Runbook Library API and Next.js page.
- Added 20 parameterised synthetic matching conditions.
- Added 30 parameterised runbook completeness conditions.
- Added unknown-case fallback and seed-count verification.
- Added runbook-library documentation.

## 1.1.0 — Temporary incident sources

- Added PDF, JSON, CSV, TXT, and LOG incident extraction.
- Added editable extraction preview before incident creation.
- Added private temporary source-file metadata and Django migration `0002`.
- Added selectable 7-day or 10-day retention.
- Added Cloudflare R2 storage with lifecycle-specific prefixes.
- Added local private storage mode for development.
- Added re-extraction and early deletion actions.
- Added structured information gaps to incidents and runbooks.
- Added missing-information collection guidance and safe fallback actions.
- Added source retention metadata to draft and final PDF reports.
- Added sample upload files and backend integration coverage.
