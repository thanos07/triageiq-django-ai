# Deployment checklist

## Neon

1. Create a free PostgreSQL project.
2. Copy the pooled connection string.
3. Set it as `DATABASE_URL` in the Django deployment.
4. Run `migrate` and `seed_demo` from a trusted local environment.

## Cloudflare R2 temporary source storage

1. Create a **private** R2 bucket.
2. Create bucket-scoped read/write credentials.
3. Add two lifecycle rules:
   - `temporary-incidents/7-days/` → expire after 7 days;
   - `temporary-incidents/10-days/` → expire after 10 days.
4. Set:

```env
TEMP_UPLOAD_STORAGE_MODE=r2
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=triageiq-temporary-files
```

See `docs/temporary-uploads.md` for the complete policy and lifecycle JSON.

## Django backend on Vercel

- Project root: `backend`
- Python entrypoint: `api/index.py`
- Required variables: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DATABASE_URL`.
- Add the R2 variables above when source uploads are enabled.
- AI variables are optional when `AI_MODE=mock`.
- Test `/api/health/` after deployment.
- Run migrations after adding temporary-file migration `0002`.

The default source-file limit is 4 MB. Browser uploads pass through Django for synchronous extraction, so keep the application limit below the serverless request-body limit. Heavy OCR and large diagnostic bundles belong in a later worker-based architecture.

## Next.js frontend on Vercel

- Project root: `frontend`
- Set `NEXT_PUBLIC_API_URL=https://backend.example/api`.
- Confirm the exact frontend origin is included in `CORS_ALLOWED_ORIGINS`.
- R2 credentials must never be added to the frontend project.

## Production hygiene

- Change or remove the seeded demo password.
- Use a strong Django secret key.
- Do not expose database or R2 credentials to the frontend.
- Keep the R2 bucket private.
- Confirm both lifecycle rules are enabled before public use.
- Restrict allowed hosts and CORS origins.
- Use the final report only after a verified resolution record exists.
