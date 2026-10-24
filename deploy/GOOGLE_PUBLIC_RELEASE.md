# Google OAuth public-release checklist

Prepared on 15 October 2026 from the official references below. **Google approval, domain verification, production consent and security assessment have not been demonstrated. Public launch remains blocked.** Application login currently admits existing linked users or explicit server-side invitations; this is a limited beta policy, not open signup.

## Public pages and contacts

- Publish a publicly accessible homepage on the verified production domain, describing inbox-nizer's mailbox organization, Search, Ask Mail and Tasks. Link the privacy policy and terms; a login-only screen is not the required homepage. Configure the same brand name and URLs in Google Auth Platform. Use separate development/test and production projects and exact HTTPS redirect URIs. [Production policy guidance](https://developers.google.com/identity/protocols/oauth2/production-readiness/policy-compliance)
- Publish the privacy policy on the homepage's domain, visible without login and linked from both the homepage and consent screen. Disclose access, use, storage and sharing of Google data. Configure a monitored support address plus current developer/owner contacts; operator identity, contacts, final URLs and retention periods must be supplied before publication. [Brand verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification)
- The implementation stores email content and derived summaries, categories, tasks, facts and embeddings in PostgreSQL; refresh credentials are encrypted. Inference is local to the application server. Describe this accurately, including who operates that server, backup retention, deletion requests and any authorized human review. Disconnect currently removes the local credential and stops new sync; it preserves imported mail. It is not account/data deletion or proof of revocation at Google. The operator-only deletion command is a support workflow; publish an accessible deletion process and test it before launch.

## Scopes and redirect URIs

| Flow | Requested scopes | Justification |
| --- | --- | --- |
| Application sign-in | `openid`, `userinfo.email` | Verified stable identity and email for invited account linking; no Gmail access. The unused profile scope has been removed. |
| Explicit Settings → Connect Gmail | `https://www.googleapis.com/auth/gmail.readonly` | Sync message bodies/metadata for Inbox, categories, Search, source-grounded Ask and Tasks. Metadata-only access cannot supply message-body evidence. No send, modify or delete scope is requested. |

`gmail.readonly` is **restricted**, despite being read-only. Server storage/transmission of restricted-scope data requires a security assessment under Google's requirements; local/free inference does not remove server handling of mailbox data. [Gmail scope classification](https://developers.google.com/workspace/gmail/api/auth/scopes)

Register `https://<production-host>/api/auth/google/login/callback` for sign-in and `https://<production-host>/api/auth/google/callback` for Gmail consent. Set `BROWSER_ORIGIN=https://<production-host>` without a trailing slash. Match the web-client console entries exactly. Keep loopback HTTP callbacks in the separate development project. Code uses state/PKCE, OIDC nonce and ID-token verification, browser binding, separate consent and revocable Secure sessions; these need a real production-browser acceptance run.

## Review submission evidence

1. Verify domain ownership and branding; declare all actual scopes. Confirm the permitted application type as an email productivity tool. Supply the app description, narrow scope justification, public policy links and a reviewer-access plan that works with the application invitation policy.
2. Record a demonstration showing the English sign-in and separate Gmail consent, correct app name/client ID, each Gmail-dependent feature, disconnect and deletion-request path. Use a dedicated demonstration mailbox; never publish private mailbox evidence.
3. Complete restricted-scope verification and the required assessment with a Google-approved assessor, address findings, and record the approval/assessment artifacts and renewal owner. Google's guidance specifies recurring assessment at least every 12 months where applicable. Verification is an external process; passing repository tests is not approval. [Restricted-scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification)
4. Review the final policy and implemented behavior against Google's Limited Use rules. Do not use Gmail-derived data for advertising or generalized model training. Private development diagnostics, human access and any personalized training must be reviewed against the actual allowed purpose and permissions; synthetic/public training data and reviewed private evaluation labels must remain distinguishable. [Workspace user-data policy](https://developers.google.com/workspace/workspace-api-user-data-developer-policy), [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy)

Record responsible owner, evidence link and completion date for each item. This repository supplies the checklist and technical controls; the public legal text, actual contacts/domain, Google Console changes, assessment and approval remain operator work. No paid service or external publication was initiated.

## Final operator evidence register (17 October 2026)

| Requirement | Exact item to record | Status |
| --- | --- | --- |
| Domain and branding | Actual production hostname, ownership verification, matching application name | Not supplied/verified |
| Homepage and privacy | Public same-domain URLs, no-login accessibility, accurate Gmail data usage and local server inference disclosure | Not supplied/verified |
| Support and ownership | Monitored support address and responsible operator | Not supplied/verified |
| Retention/deletion | Concrete retention periods, backup expiry, user deletion-request process and tested deletion evidence; disconnect alone preserves mail | Not supplied/verified |
| Redirects | `https://<production-host>/api/auth/google/login/callback` and `https://<production-host>/api/auth/google/callback`, identical to production environment and Console | Template verified; actual host unverified |
| Gmail scope | `gmail.readonly` for mailbox bodies/metadata and derived features; separate `openid email` login | Code/checklist reviewed; Console declaration unverified |
| Verification/assessment | Applicable Google restricted-scope approval, assessment completion and renewal owner/evidence | No approval claimed |
| Deployed browser | Login, separate consent, logout/session expiry, CSRF, Secure cookies and source navigation on actual HTTPS origin | Not executed |

Restricted-scope requirements and History behavior were rechecked against the linked official Google documentation during this gate. No public pages, domain settings, Console entries, assessment or external communication were changed. These remain manual evidence gates, not tasks silently marked complete by repository tests.
