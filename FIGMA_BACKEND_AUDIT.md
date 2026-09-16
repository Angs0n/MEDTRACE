# Figma-to-backend audit

Audited against Figma file `BIIWmDGprM8JWN3pWdjJru`, including the mobile
patient/provider flow and desktop patient/provider dashboards.

## Supported product flows

| Figma screens | API contract |
| --- | --- |
| Sign up, patient login, provider login | `POST /api/auth/register`, `POST /api/auth/login` |
| Personal-information onboarding and review | `PATCH /api/patient/profile`, `GET /api/patient/records` |
| Conditions, allergies, medications, procedures | Patient record create/delete endpoints and `GET /api/patient/records` |
| Patient dashboard and medical profile | `GET /api/patient/dashboard`, `GET /api/patient/records` |
| My QR Code / show / download / share | `GET /api/patient/qr.png`; download/share are browser actions on that image |
| Emergency profile | `GET /api/emergency/{qr_token}` returns only the emergency subset |
| Patient access request and history | `GET /api/access/requests`, decision/revoke endpoints, `GET /api/patient/access-history` |
| Provider dashboard, scan QR, patient found, request sent | Provider dashboard, QR lookup, and access-request endpoints |
| Provider patient medical profile | `GET /api/patients/{patient_id}/records`, only after approval |
| Provider Patients and Access History navigation | `GET /api/provider/patients`, `GET /api/provider/access-history` |

All profile responses provide `passport_id` (such as `MT-000123`) for the
patient-ID text shown in the provider desktop screens. The database ID never
needs to be invented in the frontend.

## Intentional frontend-only actions

- Welcome-page navigation, confirm-password matching, log out, QR image
  download/share, and responsive mobile/desktop layout are client actions.
- Search and filter controls on the access-history page can filter the returned
  history locally for an MVP. Add server pagination/filtering when histories
  become large.

## Not implemented: requires a real identity/communications service

The Figma file includes **Verify Code** and **Forgot Password** UI. The API does
not claim to send SMS/email codes or reset passwords because doing so without a
configured provider would be a non-functional security feature. Before those
buttons are enabled, choose Firebase Auth, Auth0, Twilio Verify, or an email
provider and add the required credentials, delivery callbacks, expiry, and
rate limiting. Provider organisation verification should use the same real
identity process.

The Figma navigation also contains Settings and notification icons but provides
no settings or notification-detail screens. They should remain navigational
placeholders until their product requirements are defined.
