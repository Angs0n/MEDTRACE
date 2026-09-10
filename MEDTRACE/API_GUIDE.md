# Frontend integration guide

## Base URL and error handling

Local base URL: `http://127.0.0.1:8000`

Production base URL: the Render service URL. The root endpoint returns service metadata, and `/docs` provides interactive Swagger documentation.

Successful protected requests use a JWT bearer token. `401` means the token is missing or expired, `403` means the role or consent is insufficient, `404` means the resource does not exist, and `409` means a state transition is no longer valid.

Set the frontend API base URL to the deployed API URL, for example `https://medtrace-api.onrender.com`.

Send the login or registration response token on protected requests:

```ts
const headers = { Authorization: `Bearer ${accessToken}` };
```

## Patient screens

- Register: `POST /api/auth/register` with `role: "patient"`
- Dashboard: `GET /api/patient/dashboard`
- Profile: `GET` or `PATCH /api/patient/profile`
- Medical profile: `GET /api/patient/records`
- Add conditions: `POST /api/patient/conditions`
- Add allergies: `POST /api/patient/allergies`
- Add medications: `POST /api/patient/medications`
- Add procedures: `POST /api/patient/procedures`
- QR image: `GET /api/patient/qr.png`
- Consent inbox: `GET /api/access/requests`
- Approve/reject: `PATCH /api/access/requests/{id}` with `{ "approved": true }`
- Revoke approved access: `POST /api/access/requests/{id}/revoke`
- Audit history: `GET /api/patient/access-history`
- Delete a condition, allergy, medication, or procedure: `DELETE /api/patient/{type}/{id}`

## Provider screens

- Register: `POST /api/auth/register` with `role: "provider"` and `organization`
- Dashboard: `GET /api/provider/dashboard`
- Consent-approved patient list: `GET /api/provider/patients`
- Provider's own record-access history: `GET /api/provider/access-history`
- Scan result is the QR token string
- Patient found preview: `GET /api/patients/lookup/{qr_token}`
- Request access: `POST /api/access/requests` with `{ "qr_token": "...", "reason": "..." }`
- Sent requests: `GET /api/access/requests`
- Full approved record: `GET /api/patients/{patient_id}/records`

## Emergency screen

Emergency mode requires no login in this MVP. The scanner sends the QR token to:

`GET /api/emergency/{qr_token}`

The response contains only the emergency-safe subset: patient name, blood group, emergency contact, allergies, active medications, major conditions, and major procedures. It does not expose address, date of birth, QR token, or other full-profile fields. Every lookup creates an access-history entry.

## Frontend request example

```ts
const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export async function api<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
	const response = await fetch(`${API_URL}${path}`, {
		...options,
		headers: {
			"Content-Type": "application/json",
			...(token ? { Authorization: `Bearer ${token}` } : {}),
			...(options.headers ?? {}),
		},
	});
	if (!response.ok) throw new Error((await response.json()).detail ?? "Request failed");
	return response.status === 204 ? (undefined as T) : response.json();
}
```

## Hosting sequence

1. Push this folder to GitHub.
2. Create a PostgreSQL database in Neon or Supabase and copy its connection string. `postgres://` and `postgresql://` values work directly; the API selects the bundled psycopg v3 driver.
3. In Render, create a new Blueprint from the repository. Render uses `render.yaml`.
4. Set `DATABASE_URL` to the PostgreSQL connection string.
5. Set `CORS_ORIGINS` to the exact Vercel frontend URL.
6. Deploy and open `/docs` on the Render URL.
7. Set the Vercel frontend environment variable, for example `VITE_API_URL=https://medtrace-api.onrender.com`.

Do not use real patient data for the hackathon demo. HTTPS, identity verification, encryption policies, backups, consent expiry, rate limiting, emergency-access policy, and compliance review are required before production use.
