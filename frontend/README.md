# AI Smart Inbox — frontend foundation

Arabic-first authenticated application. The AI/backend baseline remains frozen.

## Local development

Requires Node 22.12+ and npm (tested with Node 24.11.1). From `frontend/`:

```powershell
npm ci
Copy-Item .env.example .env
npm run dev
```

Open http://localhost:5173. The existing backend must be running at
http://localhost:8000. From the repository root, if needed:

```powershell
.\env\Scripts\python.exe -m uvicorn main:app --host localhost --port 8000 --no-access-log
```

`npm install` is also supported. The lockfile records exact dependency versions.
`VITE_API_BASE_URL` defaults to `/api`. The development proxy strips `/api` and
forwards requests to `API_PROXY_TARGET` (default http://localhost:8000). No backend
CORS changes are needed. `/api/` maps to the backend health route.

All `VITE_*` values are public browser configuration. Never put bearer tokens,
Google client secrets or encryption keys there. A different API origin requires
an explicitly reviewed CORS setup, which this phase does not implement.

The Vite proxy is development-only. Production needs same-origin `/api/` reverse
proxying, SPA history fallback, TLS, security headers and production browser auth.
`npm run preview` previews built assets; it is not a production API proxy.

## Stack and structure

React 19, TypeScript 5.9 in strict mode, Vite 7, React Router 7, TanStack Query 5,
Tailwind 4 semantic tokens, Radix Dialog and Lucide. TypeScript 5.9 matches the
OpenAPI generator's supported peer range. Actual versions are in package-lock.json.

```text
src/
  app/                    routing, locale, QueryClient and keys
  api/                    transport and feature adapters
    generated/            generated OpenAPI declarations; do not edit
  auth/                   memory-only development authentication
  components/
    layout/               responsive application shell
    shared/               loading, empty and error states
    ui/                   direction-safe text helpers
  features/
    inbox/ email/ search/ ask/ tasks/ settings/
  styles/                 semantic tokens and responsive CSS
  test/                   synthetic fixtures, MSW and regression tests
scripts/                  API generation and browser smoke check
```

Routes: `/`, `/email/:id`, `/search`, `/ask`, `/tasks`, `/settings`, and a 404
fallback. Detail uses a full routable page at every size; split-pane work is deferred.
Inbox page/filter parameters live in the URL for back/forward behavior. Private
search text and AI questions remain component state, not navigation URLs.

## API generation and contract gaps

`openapi.json` is a snapshot from the running FastAPI backend. The generated
declarations supply `/ask` types and inbox query parameter types.

```powershell
# Reproduce from the reviewed snapshot:
npm run api:generate
# Explicitly refresh from the running backend:
$env:OPENAPI_URL='http://localhost:8000/openapi.json'
npm run api:generate
Remove-Item Env:OPENAPI_URL
```

Never hand-edit `src/api/generated/schema.d.ts`. Most other backend response
schemas are currently empty in OpenAPI. Only those gaps use runtime Zod adapters
in `api/contracts.ts`, based on email_serialization.py, routes.py,
account_routes.py and gmail_sync.py. Unknown fields are discarded, including bodies
returned by sync. Invalid response shapes become safe contract errors.

Actual endpoints used:

- `GET /`: public health.
- `GET /emails`: count/total/limit/offset, body omitted; category, priority,
  task/deadline flags, sorting and SQL pagination.
- `GET /emails/{id}`: stored body, metadata, summary, predictions, tasks/deadlines.
- `GET /search/semantic`: explicit-submit discovery; scores are not shown as confidence.
- `POST /ask`: frozen answer modes; clarification sends question plus email_id.
- `GET /gmail/accounts`: scoped Gmail identity, connection state and last sync.
- `POST /gmail/accounts/{id}/sync`: explicit user action only.
- `POST /auth/google/start`: user-triggered consent handshake.
- `GET /auth/google/callback`: existing backend callback returning JSON.

There is no current-user profile endpoint, independent task-list API or
structured-fact browsing API. Settings does not invent a user identity. Tasks
links to emails with tasks instead of secretly aggregating a mailbox in JavaScript.
Email detail does not invent structured facts. No backend files were changed.

## Development authentication

Enter an already authorized operator-issued application bearer token in the password
field. GET /gmail/accounts validates it. It lives only in the authenticated React
session and is cleared on reload, logout or 401. No localStorage/sessionStorage,
token logging, token URLs, token Vite variables or token display in Settings.

AuthProvider owns login/bootstrap/logout. `useAuth()` exposes the API client,
getAccessToken(), getCurrentUser() and logout(). Current user reports only an
operator-token session with no profile API. Gmail consent is separate from app
login. Future browser SSO should replace this adapter rather than feature components.

Each session owns a fresh QueryClient and abort controller. Logout/401 aborts
requests, clears query/mutation cache and unmounts private state. A subsequent
user cannot inherit the previous user's inbox or answers.

This is a development flow, even in a production-build preview, not completed
browser authentication. Memory storage limits persistence but does not defeat XSS.

### Gmail consent

Use localhost consistently for frontend, backend and the backend's configured
redirect URI; do not mix it with 127.0.0.1. The proxy preserves the HttpOnly nonce
cookie and callback path. Cookies are host-scoped rather than port-scoped, so the
localhost callback on port 8000 receives the nonce. No cookie-path rewrite is used.

Click Connect, then Continue to Google in the same browser. A new tab preserves
the frontend's in-memory session. After the backend JSON callback succeeds, close
that tab and Refresh status. The backend handshake expires after ten minutes.
Only HTTPS accounts.google.com authorization destinations are accepted.
Production proxy/cookie/redirect paths must be configured together. Live consent
and sync were not executed during this foundation validation.

## Server state and errors

TanStack Query owns inbox, detail, search and accounts, with centralized query keys.
Default stale time is 30 seconds and garbage collection is five minutes; search
uses 60 seconds. No window-focus refetch. Only network reads retry once; search
and mutations do not automatically retry. Ask is an explicit mutation, with no
inactive mutation retention or automatic expensive generation. Sync invalidates
accounts/emails and clears stale search results.

Transport adds bearer headers, abort signals and no-store. Error UI normalizes
401/403/404/409/422/503/network/contract/unknown failures without exposing backend
detail strings. A 401 ends the session. Owned-resource 404 does not reveal ownership.
Provider failure remains distinct from insufficient evidence.

## RTL, accessibility and design

Initial `<html lang="ar" dir="rtl">` switches to English/LTR using the language
button. Logical CSS controls layout. ContentText uses dir=auto for email/answer
text; Identifier uses bdi dir=ltr for dates, times, addresses and codes.

Desktop uses sidebar plus content. Tablet keeps a narrower sidebar and one content
region. Mobile below 760px uses a single surface and Radix drawer with focus trap,
Escape dismissal and focus restoration. No three-column phone view.

Theme tokens define surfaces, borders, text, accent, warning/error and focus colors.
Typography, spacing, badges and controls are shared. No decorative dashboard,
tracking scripts, remote fonts or animation dependency. Dark mode is deferred.
Semantic landmarks, skip link, labeled forms, real buttons/links, visible focus,
loading statuses and error alerts are included. Full assistive-technology testing
remains later product work.

## Mandatory AI visual contract

- Original stored text has a separate source section; no untrusted HTML rendering.
- Summary/classification/tasks are derived assistance, not original text or truth.
- Only source_supported together with deterministic_fact or extractive earns the
  Source-supported marker. This is not independent truth verification.
- Generated synthesis always has a persistent warning about conditions, negation
  and exceptions. The backend's own prefixed notice remains verbatim too.
- Missing/conflicting/unknown metadata never implies verified output.
- Clarification is normal: show up to five valid options; resend the submitted
  question, not an edited draft, with the selected positive email_id.
- Insufficient evidence is calm, not a red operational error.
- Cited, valid sources open email-detail routes. No answer triggers an action or
  becomes a confirmed obligation automatically.

## Validation

```powershell
npm run api:generate
npm run typecheck
npm run lint
npm test
npm run build
npm run format:check
```

Vitest, Testing Library and MSW use only synthetic messages. No real GGUF, Gmail,
paid API or production writes are used by tests.

Optional small browser smoke check: start npm run dev, then npm run ui:check.
Use Node 24+ for this script's native TypeScript fixture import. It uses installed
Microsoft Edge through Playwright and mocks only /api requests. It checks 1440px,
820px and 390px, overflow, RTL, browser back, mobile focus restoration, generated
warnings and empty private storage. Screenshots/JSON go to ignored test-results/.
UI_BROWSER, UI_URL and UI_ARTIFACT_DIR are configurable. This is not a large E2E suite.

Windows Codex sandbox execution may need permission for esbuild/browser processes.
Normal developer terminals need no alternate Python or PYTHONPATH changes.

## Security and remaining work

No backend secrets/private samples are shipped. No dangerous HTML rendering,
token persistence, analytics, email-body logging or raw exception display. VITE
configuration is public. OAuth/sync require explicit actions. Test mocks are not
part of the production entry point. Source metadata is always rendered as text.

Remaining: browser production auth/SSO, deployment proxy/security headers, dedicated
task/fact/profile APIs if desired, detailed user/accessibility testing, optional
split pane and feature polish. OAuth currently ends at existing backend JSON.
Historical extraction accuracy and synthesis limitations remain frozen.

References: [Vite proxy](https://vite.dev/config/server-options),
[OpenAPI TypeScript](https://openapi-ts.dev/cli),
[TanStack Query](https://tanstack.com/query/latest/docs/framework/react).
