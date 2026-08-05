# Temporary incident source files

TriageIQ can extract incident facts from **PDF, JSON, CSV, TXT, and LOG** files. The original source is private and temporary; the structured incident record is permanent until the user deletes the incident.

## Retention choices

Users select either **7 days** or **10 days** while uploading. TriageIQ writes objects into a retention-specific R2 prefix:

```text
temporary-incidents/7-days/<random-id>.<ext>
temporary-incidents/10-days/<random-id>.<ext>
```

The application stores `expires_at` in PostgreSQL and blocks re-extraction immediately at that timestamp. Cloudflare R2 lifecycle rules perform the physical deletion without a cron job, Celery worker, Render service, or always-on Django process.

## Cloudflare R2 setup

1. Create a private R2 bucket, for example `triageiq-temporary-files`.
2. Create an R2 API token that can read and write only this bucket.
3. Configure the backend:

```env
TEMP_UPLOAD_STORAGE_MODE=r2
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<access-key>
R2_SECRET_ACCESS_KEY=<secret-key>
R2_BUCKET_NAME=triageiq-temporary-files
```

Do not expose these values to Next.js.

## Lifecycle rules

Create two object lifecycle rules in the R2 bucket:

| Rule | Prefix | Expiry |
|---|---|---|
| `delete-7-day-incident-files` | `temporary-incidents/7-days/` | 7 days |
| `delete-10-day-incident-files` | `temporary-incidents/10-days/` | 10 days |

Equivalent S3-compatible lifecycle configuration:

```json
{
  "Rules": [
    {
      "ID": "delete-7-day-incident-files",
      "Status": "Enabled",
      "Filter": { "Prefix": "temporary-incidents/7-days/" },
      "Expiration": { "Days": 7 }
    },
    {
      "ID": "delete-10-day-incident-files",
      "Status": "Enabled",
      "Filter": { "Prefix": "temporary-incidents/10-days/" },
      "Expiration": { "Days": 10 }
    }
  ]
}
```

R2 may physically remove an expired object after the exact application expiry time. TriageIQ still treats the file as unavailable as soon as `expires_at` is reached.

## Local development

The default configuration uses local private storage:

```env
TEMP_UPLOAD_STORAGE_MODE=local
TEMP_UPLOAD_LOCAL_ROOT=.temporary-uploads
```

The folder is ignored by Git. Local files are not deleted by an R2 lifecycle rule, so delete them from the incident screen or remove the local folder during development.

## Extraction behaviour

- **PDF:** text-based PDFs only, up to 25 pages.
- **JSON:** object or array of objects; the first record is previewed.
- **CSV:** the first non-empty row is previewed.
- **TXT:** plain UTF-8 text.
- **LOG:** relevant error/warning lines are selected and obvious secrets are redacted.

The free deployment defaults to a 4 MB file limit. The original binary is never stored in PostgreSQL. PostgreSQL stores only:

- private object key;
- original file name and MIME type;
- size and SHA-256 hash;
- upload and expiry timestamps;
- extracted structured fields;
- extraction context and information gaps;
- link to the confirmed incident.

## Missing information

Extraction never invents missing values. Missing service, environment, impact, timing, or diagnostic evidence is stored in `Incident.information_gaps`. The root-cause and runbook agents receive these gaps. The runbook then explains:

- why each item is needed;
- how to collect it;
- whether it blocks confident resolution;
- what safe fallback action to use meanwhile.

## Security controls

- Private bucket only; no public R2 domain.
- Random object keys rather than original file names.
- Extension, signature, encoding, page, line, and size validation.
- Executables and unknown binary formats rejected.
- Obvious credentials redacted from extracted LOG/TXT evidence.
- Source file can be deleted early from the incident workspace.
- Re-extraction preserves human-edited incident fields.
- AI cannot resolve an incident automatically.
