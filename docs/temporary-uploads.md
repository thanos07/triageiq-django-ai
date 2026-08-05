# Temporary incident source files

TriageIQ can extract incident facts from **PDF, JSON, CSV, TXT, and LOG** files. The original source file remains private and temporary. The structured incident record and audit history remain available after the original file is deleted.

## Retention choices

Users select either **7 days** or **10 days** while uploading. TriageIQ stores each private object under a retention-specific key:

```text
temporary-incidents/7-days/<random-id>.<ext>
temporary-incidents/10-days/<random-id>.<ext>
```

The application stores an `expires_at` timestamp in PostgreSQL and prevents re-extraction once that timestamp is reached.

A scheduled cleanup job then:

1. finds expired temporary-file records;
2. deletes the original object from private storage;
3. marks the database record as deleted;
4. records the deletion time;
5. keeps extracted incident data and audit history unchanged.

When a storage deletion fails, the database record remains unchanged so that a later cleanup execution can retry it.

## Supabase Storage setup

Production uses a private Supabase Storage bucket through its S3-compatible API.

Example bucket name:

```text
triageiq-temp-uploads
```

Configure the backend with:

```env
TEMP_UPLOAD_STORAGE_MODE=s3

S3_ENDPOINT_URL=https://<project-ref>.storage.supabase.co/storage/v1/s3
S3_ACCESS_KEY_ID=<access-key>
S3_SECRET_ACCESS_KEY=<secret-key>
S3_BUCKET_NAME=triageiq-temp-uploads
S3_REGION=<supabase-region>
S3_FORCE_PATH_STYLE=true
```

Keep the bucket private.

Never expose storage credentials to Next.js, include them in screenshots, or commit real credentials to GitHub.

## Scheduled cleanup

Vercel invokes the protected cleanup endpoint once per day:

```text
GET /api/cron/purge-expired-uploads/
```

The request must include the configured bearer token:

```text
Authorization: Bearer <CRON_SECRET>
```

Backend configuration:

```env
TEMP_UPLOAD_CLEANUP_BATCH_SIZE=100
CRON_SECRET=<strong-random-secret>
```

`TEMP_UPLOAD_CLEANUP_BATCH_SIZE` limits the maximum number of expired files processed during one execution.

The production schedule is defined in the root `vercel.json` file.

Example configuration:

```json
{
  "crons": [
    {
      "path": "/api/cron/purge-expired-uploads/",
      "schedule": "0 2 * * *"
    }
  ]
}
```

The cleanup endpoint rejects requests when:

- `CRON_SECRET` is not configured;
- the `Authorization` header is missing;
- the bearer token does not match the configured secret.

A successful request returns a summary similar to:

```json
{
  "status": "ok",
  "scanned": 3,
  "deleted": 2,
  "failed": 1
}
```

The fields mean:

- `scanned`: number of expired records processed;
- `deleted`: number of storage objects successfully deleted;
- `failed`: number of deletions that failed and can be retried later.

## Manual cleanup

Cleanup can also be executed manually from the backend directory:

```bash
python manage.py purge_expired_uploads
```

To limit one execution:

```bash
python manage.py purge_expired_uploads --limit 10
```

Example output:

```text
Temporary-file cleanup completed: scanned=3, deleted=3, failed=0
```

The command validates that `--limit` is at least `1`.

## Local development

Local development uses private filesystem storage by default:

```env
TEMP_UPLOAD_STORAGE_MODE=local
TEMP_UPLOAD_LOCAL_ROOT=.temporary-uploads
```

The local storage folder is ignored by Git.

The same cleanup service supports local files, so expired local uploads can be removed with:

```bash
python manage.py purge_expired_uploads
```

A source file can also be deleted early from the incident workspace before its scheduled expiry time.

## Extraction behaviour

Supported file types:

- **PDF:** text-based PDFs only, up to 25 pages.
- **JSON:** an object or array of objects; the first record is previewed.
- **CSV:** the first non-empty row is previewed.
- **TXT:** plain UTF-8 text.
- **LOG:** relevant error and warning lines are selected, and obvious secrets are redacted.

The free deployment defaults to a 4 MB upload limit.

The original binary file is never stored in PostgreSQL.

PostgreSQL stores only:

- private storage object key;
- original file name;
- MIME type;
- file size;
- SHA-256 hash;
- upload timestamp;
- expiry timestamp;
- retention duration;
- deletion status;
- deletion timestamp;
- extracted structured fields;
- extraction context;
- information gaps;
- link to the confirmed incident.

## Expiry behaviour

Once `expires_at` is reached:

- the original source file is treated as unavailable;
- re-extraction is blocked;
- the record becomes eligible for scheduled cleanup;
- the structured incident record remains available;
- workflow results and audit history remain available.

The cleanup job physically removes the private object and then updates the database record to indicate that deletion succeeded.

## Missing information

Extraction never invents missing values.

Missing service, environment, impact, timing, or diagnostic evidence is stored in `Incident.information_gaps`.

The root-cause and runbook agents receive these gaps. The runbook explains:

- why each missing item is needed;
- how the information can be collected;
- whether the missing information blocks confident resolution;
- what safe fallback action can be used meanwhile.

## Failure and retry behaviour

If object deletion fails:

- the storage exception is handled safely;
- the file record is not marked as deleted;
- `deleted_at` remains empty;
- the record remains eligible for the next scheduled cleanup;
- other expired files can continue to be processed.

This prevents the database from reporting that a source file was deleted when the physical storage operation actually failed.

## Security controls

- Private storage bucket only.
- No public object URLs.
- Random object keys instead of original file names.
- File extension and MIME validation.
- File signature validation.
- Encoding, page, line, and size limits.
- Executables and unknown binary formats rejected.
- Obvious credentials redacted from extracted LOG and TXT evidence.
- Cleanup endpoint protected by a secret bearer token.
- Secret comparison performed securely.
- Source files can be deleted early from the incident workspace.
- Expired source files cannot be re-extracted.
- Failed deletions remain retryable.
- Re-extraction preserves human-edited incident fields.
- Extracted incident data remains separate from the original binary.
- AI cannot resolve an incident automatically.
- Human review remains part of the incident workflow.