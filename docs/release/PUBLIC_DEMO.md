# Public interactive demo — isolated static deployment

The public-demo task explicitly authorizes a separate synthetic-data-only website;
it does not reopen full Gmail-connected production approval.

## Architecture

The existing `inbox-nizer-beta` Python service is unchanged. Its live generated
wrapper and migration-on-start command make an incidental redeploy unsafe. The
checked-in Python build also requires an approved classifier bundle, which does not
exist. The demo instead builds the same React/Vite UI as a separate Render Static
Site with no backend, no database, no secrets and no model.

`npm run build:demo` selects `DemoApp` at build time. Ordinary `npm run build` retains
the authenticated application. DemoApp reuses InboxPage, EmailPage, TasksPage, Shell,
filters, pagination, typography and Arabic/English controls. It does not mount
AuthProvider, GmailSyncProvider, OAuth callbacks, Search/Ask or real Settings.
DemoClient serves only allowlisted in-memory reads; mutations, authentication,
unknown IDs and external origins are rejected. The normal ApiClient also fails
closed in demo builds. A demo-only HTML CSP sets `connect-src 'none'`, `form-action
'none'` and self-hosted scripts/assets. No cookies or credential storage are read.
The private app's login, ownership, CSRF, allowed-user and sync code stays intact.

All 24 messages were authored as fictional examples with `example.invalid` senders.
Their categories, summaries and ten source-linked tasks are prewritten examples,
not model predictions or actual Gmail imports. There is no connected-account claim.
Settings explains unavailable connection/sync/reprocessing actions. Classification
remains experimental; V03 provenance is verified but V10 FAILED. No model changed.

HashRouter gives supported routes `/#/`, `/#/email/1`, `/#/tasks`, `/#/settings`.
The fragment stays in the browser: refreshing any of these requests `/index.html`
from the CDN and cannot invoke a backend route. No SPA rewrite or Python fallback
is needed. Unknown hash routes render the existing Not Found view. Language choice
is session-memory UI state and resets to Arabic on reload; filters are in the hash
query. The demo remains usable when the private PostgreSQL instance expires.

## Build and verify locally

Use Node 24 and the checked-in npm lockfile:

```sh
cd frontend
npm ci --no-audit --no-fund
npm test
npm run typecheck
npm run lint
npm run build
npm run build:demo
python -m http.server 4173 --bind 127.0.0.1 --directory dist
```

In another terminal, from frontend, run `npm run demo:check`. The Playwright script
uses installed Edge by default (`UI_BROWSER` can select another installed channel).
It checks an actual built website without API mocks. `DEMO_URL` selects the website;
`DEMO_EXPECTED_SHA` checks `/demo-build.json` against the deployed commit.
`DEMO_CHECK_OUTPUT` selects a local ignored directory for synthetic screenshots and
aggregate results. Do not serve the repository root or private directories.

## Render static-site configuration

- A new isolated **Static Site**, using the existing repository/release branch.
- Build: `cd frontend && npm ci --no-audit --no-fund && npm run build:demo`.
- Publish directory: `frontend/dist`.
- `NODE_VERSION=24`, `SKIP_INSTALL_DEPS=true`. No other environment variables needed.
- Auto-deploy: **No**. No start command, Python build, migrations, database or API proxy.
- Render supplies HTTPS. `/demo-build.json` records `RENDER_GIT_COMMIT` from the build.
- No paid compute, custom domain or billing-plan change. Static sites consume the
  workspace's existing bandwidth/build-minute allowances; overages are subject to
  its billing settings. [Render static sites](https://render.com/docs/static-sites),
  [free-tier limits](https://render.com/docs/free).

The live URL and deployment identity are recorded only after deployment and real
HTTP/browser verification. A platform status of `live` alone is not acceptance.

## Private Gmail boundaries

The existing app still restores server sessions, admits existing linked users or
`GOOGLE_LOGIN_ALLOWED_EMAILS`, uses separate read-only Gmail consent and protects
cookie mutations with CSRF/origin checks. Production session cookies are Secure,
HttpOnly and host scoped. Bounded browser-driven synchronization/reconnect/disconnect
remain private functionality; the demo does not mount or bypass them. Existing
HTTPS login and Gmail callback settings are not changed or registered for the demo.
No Google Console access is claimed and no users are added.

If the Google project is in **Testing**, Gmail consent is restricted to up to 100
listed test users, displays a testing warning and expires after seven days (including
refresh tokens). The basic OIDC sign-in-only exception does not cover gmail.readonly.
The separate app invitation policy still applies. The Console's current status was
not inspected. [Google audience documentation](https://support.google.com/cloud/answer/15549945).
Recruiters do not need and are not promised Gmail authorization.

The private service remains **NO-GO**: classifier quality, exposed DB password
rotation, isolated restoration, host capacity/security and DB continuity remain
unresolved. The operator confirms temporary external DB access was removed. This
static task does not alter credentials, keys, account data, checkpoints or networking.


## Pre-deployment evidence — 25 October 2026

Clean `npm ci --no-audit --no-fund` completed from the lockfile (358 packages).
Focused demo suite: 11 passed. Complete frontend suite: 173 passed across 11 files.
Typecheck, ESLint, ordinary private build and isolated demo build passed. Existing
third-party Zod annotation warnings do not prevent either build. An initial Windows
sandbox/esbuild configuration access error was resolved by running these authorized
checks outside that sandbox. The combined multi-interaction DOM test received a
15-second timeout after exceeding the default five seconds; assertions are unchanged.

Local built-site Edge checks use real static HTTP with no mocked API: 1440/390px,
Arabic RTL/English LTR, anonymous entry, category/priority filters, pagination,
message details, summaries, task source links, settings limitations, direct routes,
refresh and unknown-route handling. They enforce zero API/external requests, zero
cookie access and no runtime/console errors. Browser test selectors and fresh-page
setup were corrected to reflect actual accessible controls and hash navigation.
The demo-specific keyboard skip link focuses the content without changing the hash.
Synthetic local screenshots were reviewed; live deployment acceptance is separate.
No manual backend suite was needed because backend code/routes remain unchanged;
the existing GitHub workflow still runs its backend checks automatically.
