# inbox-nizer frontend

Arabic/English React application with the existing retro design. The frontend
provides Inbox, Email Detail, Search, Ask Mail, Tasks and Gmail Settings.

## Local development

Requires Node 22.12+ and npm; the browser smoke scripts use Node 24+ for native
TypeScript fixture imports. From `frontend/`:

```powershell
npm ci
Copy-Item .env.example .env
npm run dev
```

Open http://localhost:5173. The development proxy forwards `/api` to
`API_PROXY_TARGET` (default http://localhost:8000), stripping the `/api` prefix.
Run the configured backend from the repository root:

```powershell
.\env\Scripts\python.exe -m uvicorn main:app --host localhost --port 8000 --no-access-log
```

All `VITE_*` values are public browser configuration. Never put credentials or
encryption keys in them. `VITE_API_BASE_URL` defaults to `/api`; production uses
the same origin. `npm run preview` serves built assets only and is not the
production API proxy. Deployment, security and Google review requirements are
documented in [deploy/README.md](../deploy/README.md).

## Authentication and Gmail consent

Production builds expose only **Continue with Google**, with the welcome text
“أهلاً بك في صندوقك الوارد المرتب” / “Welcome to your organized inbox”.
`POST /auth/google/login/start` begins application login. The backend validates
OIDC and establishes an HttpOnly browser session. On reload the frontend restores
it through `GET /auth/session`; mutating session requests carry `X-CSRF-Token`.
Signing out clears private React/query state immediately and attempts server
revocation through `DELETE /auth/session`. An unsuccessful revocation remains
visible with a retry action.

The optional token form exists only in Vite development mode. The token remains
in memory. `VITE_AUTH_MODE=browser` enables the development browser-session flow;
it does not enable a token form in a production build.

Application login and Gmail read consent are separate. A signed-in user with no
Gmail accounts is sent from Inbox to Settings. An existing connection opens Inbox.
Connect/reconnect explicitly starts `POST /auth/google/start?browser=true`, then
offers a Google link in a new tab. Only HTTPS `accounts.google.com` destinations
are accepted. The bounded `/oauth/complete` page reports the consent outcome;
refresh Settings to fetch the connection state. Sync requires an explicit click.

Use localhost consistently for local frontend, backend and configured redirect
URIs. Real Google consent, verification and hosted TLS/cookie behavior require
on-host checks; synthetic UI tests do not establish those outcomes.

## State, routing and privacy

Routes are `/`, `/email/:id`, `/search`, `/ask`, `/tasks`, `/settings`,
`/oauth/complete`, and a localized 404. Inbox and Tasks filters/pagination live in
the URL. Safe return paths restore the originating view when leaving Email Detail.
Search text/results and Ask drafts/answers/history stay in authenticated-session
memory, survive detail navigation, and clear on logout, expiry and reload.
Ask sends at most four prior successful user questions for bounded follow-ups;
the backend retrieves and validates fresh mailbox evidence for every answer.

Each authenticated session owns a fresh QueryClient and abort controller.
Logout/401 aborts requests and clears caches. No private state is written to
localStorage/sessionStorage, navigation URLs, analytics or console logs.
Untrusted message and answer content is rendered as text, never HTML.

Transport normalizes authorization, forbidden, missing, conflict, validation,
service, network and contract failures without showing backend detail strings.
No raw 422 response, exception payload, or stack trace is shown to users.

## Product behavior

- Inbox exposes Priority and multi-select Category. Category values come from
  `/email-categories`; category selection is OR, combined with priority by AND.
- Search is email discovery, not question answering. The server selects relevant
  matches and displays the result set by normalized message time, newest first.
- Tasks use `/tasks`, with newest/oldest sorting by normalized persisted task
  deadline date/time and undated tasks last. Detection accuracy is a backend
  release gate, not a frontend guarantee.
- Ask separates the natural answer from collapsed sources showing subject,
  sender, human date and an Email Detail link. Presentation removes inline
  citation markers and formats dates without discarding supported conditions,
  exceptions or negation. The current backend composes natural summaries.
- Only consistent citations plus `source_supported` and `deterministic_fact` or
  `extractive` enable the source-supported marker. It explicitly does not claim
  independently verified truth. Generated synthesis always retains its warning.
  Unknown verification does not earn the supported marker.
- Clarification shows up to five valid choices and submits the original question
  with the selected email ID. Editing the draft cannot change that question.

Arabic uses RTL and English LTR. Email content may remain mixed. Logical CSS,
direction-aware text, keyboard controls, skip links, error/status regions and a
Radix mobile drawer preserve the retro identity. Full assistive-technology
validation remains a manual release check.

## API contracts and source layout

`src/api/generated/schema.d.ts` comes from the checked-in `openapi.json` snapshot.
Do not hand-edit generated declarations. Runtime Zod adapters cover response
contracts missing from OpenAPI and discard unknown fields.

```powershell
npm run api:generate
# Explicitly refresh the snapshot from a configured local backend:
$env:OPENAPI_URL='http://localhost:8000/openapi.json'
npm run api:generate
Remove-Item Env:OPENAPI_URL
```

`src/app` owns routing/locale/query keys; `src/auth` owns authentication;
`src/api` owns transport/contracts; `src/features` contains the six product
surfaces; `src/components` provides shared UI; `src/styles` holds the theme;
`src/test` contains synthetic fixtures and regressions.

## Validation

```powershell
npm run typecheck
npm run lint
npm test
npm run format:check
npm run build
```

Vitest/Testing Library/MSW use synthetic messages. For the production-build
responsive smoke, start a separate `npm run preview -- --port 5189` and run:

```powershell
$env:UI_URL='http://localhost:5189'
$env:UI_BROWSER_AUTH='1'
npm run ui:check
```

The smoke script uses installed Edge via Playwright and synthetic API responses.
It checks widths 1440, 820 and 390, both languages, overflow, Google-only login,
session restore/logout, categories, source and task back navigation, generated
warnings, clarification, settings/sync states and empty browser storage.
`UI_BROWSER` and `UI_ARTIFACT_DIR` are configurable. Screenshots and the JSON
summary default to ignored `test-results/`. Production-build browser checks
verify compiled UI behavior; they do not call live Google, Gmail or the mailbox.

The opt-in repository `test_ask_browser.py` bridges real `/ask` responses from an
isolated rollback test database to `scripts/check-ask-integration.mjs`; it requires
the preview above and the test database safeguards in `conftest.py`. Do not point
this test at a production database. Windows sandbox execution may require
approval for esbuild and browser child processes.
