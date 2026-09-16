# Deploying MedTrace MVP

The repository is ready to deploy as a Docker-based FastAPI service. It uses
SQLite only for local demos; production must use managed PostgreSQL so records
survive restarts and can be backed up.

## Backend: Render + Neon/Supabase PostgreSQL

1. Create a PostgreSQL database in Neon or Supabase and copy its **pooled**
   connection string. On Neon, use the hostname containing `-pooler` rather
   than the direct database hostname. Render instances can lack IPv6 routing;
   a direct URL that resolves only to IPv6 produces `Network is unreachable`
   during startup.
2. Push this repository to a Git provider and, in Render, choose **New →
   Blueprint** and select the repository. Render reads `render.yaml`, builds
   the included `Dockerfile`, and deploys the API. The container honors
   Render's supplied `PORT` value.
3. In Render, set these environment variables:

   | Variable | Value | Why |
   | --- | --- | --- |
   | `DATABASE_URL` | The pooled managed PostgreSQL connection string | Stores durable shared records. Both `postgres://` and `postgresql://` are supported. Use the pooler hostname. |
   | `JWT_SECRET` | A unique, long random secret | Prevents forged login tokens. Render can generate this from the blueprint. |
   | `CORS_ORIGINS` | Your exact Vercel URL, e.g. `https://medtrace.vercel.app` | Lets only the deployed web app call this API from a browser. |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` (or your policy) | Limits how long a stolen access token remains useful. |

4. Confirm `https://<your-render-service>/health` returns `{"status":"ok"}`.
   Then visit `/docs` to exercise the live OpenAPI interface.

### PostgreSQL connection error

If Render logs show `psycopg.OperationalError` with an IPv6 address and
`Network is unreachable`, replace `DATABASE_URL` with the pooled connection
string from Neon or Supabase, save the environment variable, and redeploy.
Do not paste a local `localhost` URL or a direct IPv6-only database URL.

## Frontend: Vercel

This workspace contains the backend only, so there is no Vercel project to
deploy yet. When the React/Vite client is added, configure:

```
VITE_API_URL=https://<your-render-service>
```

Then redeploy the API with `CORS_ORIGINS` set to that Vercel deployment URL.
The two values must match exactly, including `https` and any custom domain.

## Before real patient data

The shipped emergency endpoint is intentionally unauthenticated to support the
unconscious-patient demonstration. Do not use this MVP for real clinical data
until provider verification, emergency-access policy, rate limiting, encryption
and key management, monitoring, retention rules, and a compliance/legal review
are in place.
