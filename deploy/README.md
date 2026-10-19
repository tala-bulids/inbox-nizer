# Same-origin web deployment

This is a deployment design and example, not an executed internet deployment. Review hostname, certificates, OS paths, timeouts and resource limits for your host. No Docker is required.

## Topology

HTTPS origin (e.g. https://inbox.example.com): / serves frontend/dist with SPA history fallback; /api/ proxies to loopback FastAPI. The proxy strips /api. Run uvicorn with --root-path /api so generated URLs reflect the external prefix. Bind only to loopback, trust proxy headers only from 127.0.0.1. Do not expose port 8000 publicly. There is no CORS middleware and no wildcard CORS.

Build using npm ci, npm run api:generate, npm run typecheck, npm run lint, npm test and npm run build in frontend. Serve the resulting dist directory, not Vite dev/preview. Test nginx -t on the deployment host before reload; nginx is not installed/validated in this Windows workspace.

Example backend launch using the project's environment:

    python -m uvicorn main:app --host 127.0.0.1 --port 8000 --root-path /api --proxy-headers --forwarded-allow-ips 127.0.0.1 --no-access-log

Use an OS service with a restricted user and secret environment file. Restart on failure, monitor health/status codes without logging request bodies, Authorization/Cookie headers, query strings or OAuth codes. Nginx example disables request/error logging for this private origin. Ensure load balancers/APM do not re-enable private payload logging. Keep database backups/encryption keys protected and outside the web root.

Review the [service example](inboxnizer.service), [operations and recovery runbook](OPERATIONS.md), and [Google public-release checklist](GOOGLE_PUBLIC_RELEASE.md). These are deployable examples and acceptance procedures, not evidence of an executed production deployment or Google approval.

## Browser authentication

Production uses **Continue with Google** for application sign-in (OpenID Connect `openid email` only). This does not authorize Gmail. Google ID tokens are verified server-side for signature, issuer, expiry, audience and nonce; identity is keyed by stable `sub`, never by a mutable email after linking. Login uses an origin-checked POST, PKCE, a separate HttpOnly browser-bound nonce cookie and an atomically consumed 10-minute attempt. No Google login tokens are persisted. The unused profile scope is not requested.

There is no public signup. First sign-in may link an active existing AppUser through its owned GmailAccount address only when Google is authoritative for that verified address (gmail.com or a Workspace `hd` claim). Otherwise the exact verified address must be explicitly invited in the server-only `GOOGLE_LOGIN_ALLOWED_EMAILS` comma-separated allowlist to create a separate AppUser. Non-Google-hosted email identities are not automatically linked. Each AppUser has one stable Google identity. Existing token/administrator API workflows remain, but token entry is rendered only by development builds.

Successful login rotates the browser session, sending connected users to Inbox and users without a connected mailbox to Settings for the separate Gmail consent. Denial, expired attempts, provider errors and denied account access return bounded error codes, never tokens or provider details.

Production cookie: __Host-inbox_session, Secure, HttpOnly, SameSite=Lax, Path=/, no Domain. Google sessions expire after 8 hours. The backend rejects the admin-token browser exchange outside development with HTTP 404; hiding the development form is not the security boundary. Development exchange sessions expire at the earlier of 8 hours or provisioning-code expiry. No sliding renewal. GET /auth/session restores the browser session and returns its CSRF value in a no-store response. Every cookie-authenticated unsafe request requires an exact configured Origin and a session-bound X-CSRF-Token. Legacy GET OAuth-start cannot be triggered with ambient cookie credentials alone. Bearer API authentication remains supported; browser session values cannot be used as bearer provisioning codes.

DELETE /auth/session deletes the stored digest and clears the cookie. Admin revoke-tokens invalidates all tokens/sessions for a user. Disabling an AppUser also immediately invalidates sessions at the next authenticated request. Revoking only an individual provisioning token does not automatically revoke already-created sibling sessions; revoke all user tokens when disabling access. Browser logout failures clear visible data but explicitly require retry before leaving a shared device. Existing expired AccessToken rows can be pruned by trusted maintenance; no automatic cleanup job is introduced.

The runtime database role needs SELECT/INSERT/DELETE on app_access_tokens and google_login_attempts, SELECT/INSERT on google_identities, and AppUser provisioning permissions (including sequence USAGE when allowlisted onboarding is used), not schema ownership. Apply grants through your normal administrator process if missing. No production grants were run by this task. Existing principal/OwnedSession tenant checks still protect mailbox queries.

## Environment

Backend secrets (never VITE): DATABASE_URL, OAUTH_TOKEN_KEYS, Google client credentials/config and model configuration. TEST_DATABASE_URL must point to a separate _test database.

Backend public configuration:

    APP_ENV=production
    BROWSER_ORIGIN=https://inbox.example.com
    GOOGLE_REDIRECT_URI=https://inbox.example.com/api/auth/google/callback
    GOOGLE_LOGIN_REDIRECT_URI=https://inbox.example.com/api/auth/google/login/callback

Register both exact callbacks in the Google OAuth console. BROWSER_ORIGIN must be an origin without trailing slash/path; no user-provided redirect target is accepted.

Frontend public build configuration:

    VITE_API_BASE_URL=/api

Production builds always use browser-session auth. Development builds also show an operator-token fallback; Google login and session restoration remain available. Set VITE_AUTH_MODE=browser to exercise cookie auth locally. Local backend defaults BROWSER_ORIGIN=http://localhost:5173 and callback=http://localhost:8000/auth/google/callback; use localhost consistently on both ports so the nonce cookie reaches the callback. APP_ENV=development allows the unprefixed non-Secure loopback session cookie. Never deploy with APP_ENV=development. API_PROXY_TARGET is a Vite development-server setting, not a production browser variable. Never put keys, URLs containing passwords or tokens into any VITE variable.

## OAuth presentation

Frontend POSTs /auth/google/start?browser=true, then opens only an HTTPS accounts.google.com URL without userinfo or a nondefault port. Existing nonce/state/PKCE checks and one-use attempts remain. Browser callback redirects only to configured BROWSER_ORIGIN/oauth/complete with a bounded result: success, denied, expired or provider_error. Codes/tokens/private details are never forwarded. The page tells the user to open Settings to confirm account status; the URL itself is not proof of connection. Non-browser clients keep the legacy JSON/error responses.

## Headers and cache

See nginx.conf for TLS redirect, HSTS, CSP, no-referrer, nosniff, frame denial and permissions policy. CSP permits scripts only from self; no eval/inline scripts/remote CDN. Inline styles are permitted because Radix uses inline presentation styles. HTML is uncached, fingerprinted assets are cached, API middleware forces no-store. Only dist is public; .env, credentials, backups, Python sources and repositories must never be under the static root.

## Release checks

Run frontend validation and full backend auth/security regression tests. Check HTTPS cookie flags, login/refresh/logout/revocation, CSRF denial, Google consent success/denial/expired/provider outcomes, direct SPA deep links, mobile focus and all AI result states on the configured deployment host. Current local tests use synthetic responses; they do not replace real TLS/reverse-proxy and Google-console acceptance checks.

References: [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [OWASP CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html), [FastAPI behind a proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/).

## Google login activation (manual)

Migration `c4d9e6f135ab_google_signin.py` follows `b3c8d5e024fa`. It only adds Google identities and login attempts; it does not change or backfill inbox data. The 15 October 2026 read-only audit found the mailbox database already at this revision. This pass performed migration roundtrip tests only in the isolated test database and did not migrate the mailbox database.

For a separate deployment that is behind this revision, first follow the backup, owner-role and verification procedure in [OPERATIONS.md](OPERATIONS.md). From the repository directory, after confirming the operator connection targets the intended database and reviewing the migration:

```powershell
.\env\Scripts\python.exe -m alembic upgrade head
```

Register `http://localhost:8000/auth/google/login/callback` for local development in the existing web OAuth client's authorized redirect URIs. Keep its existing Gmail callback too. In production use the two HTTPS `/api/` callbacks above. Restart the backend after configuration. Never put the client secret, allowlist, token encryption keys or database URL in `VITE_*` variables. Google Console configuration and real browser consent still need operator verification; mocked tests cannot prove they are configured.

Identity verification follows [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect) and [Google's ID-token verification guidance](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).
