# Portfolio source release freeze — 25 October 2026

**PORTFOLIO SOURCE RELEASE: COMPLETE**

**HOSTED PRODUCTION RELEASE: NO-GO**

This is a source/portfolio freeze, not production acceptance. The repository is
[Inbox-nizer](https://github.com/tala-bulids/inbox-nizer), with verified default branch
`codex/inbox-nizer-release`. Neither default branch nor repository description was
changed in this pass. No merge into `main`, force push, deployment, live migration,
credential rotation, networking change or mailbox deletion is part of this release.

## Frozen scope and provenance

The application candidate remains `b3225fa0b6e2863aae1c445f1789d3303fabd8e1`.
`1d37c4647f45bef5762b432be08f6a12f856f23f` supplies the honest README and synthetic
portfolio gallery. `1c987bdbbb20cbc920275a8e287837987981345f` records V03/V10 evidence.
The final freeze commit changes documentation only and preserves all those commits.
Its identity is the commit containing this ledger; final remote HEAD and CI results
are verified after publication in the handoff. [GitHub Checks](https://github.com/tala-bulids/inbox-nizer/actions/workflows/ci.yml)
record each published SHA; a previous green run is not a claim about a new run.

Classification is **experimental and not production approved**. The existing FP32
ONNX artifact matches checkpoint-3159 at weight SHA-256
`97a26b679690d2ab8df85f4e5b8fab2b7c91c8011807ac04767c4a9790a1e3d4`.
Fresh parity passed 111/111 inputs; max score difference 0.00000301003456, tolerance
0.0001. All source/export hashes are frozen in [aggregate evidence](v03-v10-20261024.json).
The original training split/report is unavailable. V03 provenance is verified;
classifier release approval is blocked. V10 remains FAILED, rating C.

Consumed difficult-development diagnostics: English 20/56, Arabic-heavy 1/11,
overall 32/100, top-one macro-F1 0.2839. These heuristic language slices are not
representative accuracy or untouched holdout results. The existing policy is unchanged.
See [V03/V10 evidence](V03_V10_EVIDENCE.md) for coverage, caveats and failed gates.

## Every release item: source completion versus production acceptance

A = fully completed and verified for its stated scope. B = implemented/complete for
portfolio source, with hosted operation unapproved. C = genuinely blocked by a
missing prerequisite or failed gate. These dispositions do not waive the existing
PROJECT_STATUS.md / RENDER_RELEASE.md production contract.

| Item | Class | Final disposition |
| --- | --- | --- |
| V01 | A | Source/worktree consolidation recorded; history and experimental work preserved. |
| V02 | C | Host inventory recorded; actual configuration, schema/role and session-affinity acceptance remain unavailable. |
| V03 | A / C | Exact artifact provenance and fresh parity verified; original training lineage incomplete and production-model approval blocked by V10. |
| V04 | B | Reproducible recipe and local serving checks complete; approved artifact and fresh target-host build not accepted. |
| V05 | B | Hosted capability gates implemented/tested; deployed candidate acceptance remains separate. |
| V06 | B | Stable message-date ordering implemented/tested. |
| V07 | B | Bounded enrichment recovery and truthful sync status implemented/tested. |
| V08 | B | Durable failed-source handling, bounded attempts and cursor invariants implemented/tested. |
| V09 | B | Disconnect/reconnect, retention and authorization boundaries implemented/tested. |
| V10 | C | Quality gate FAILED; no representative untouched human-reviewed final holdout, no approved classifier. |
| V11 | C | Local security tests pass; operator confirms temporary IP rule removed. Exposed password rotation deferred and hosted controls unverified. |
| V12 | C | No accepted target Render memory/concurrent-load evidence. |
| V13 | A | Application regression evidence recorded below; final published HEAD must also have successful GitHub backend/frontend checks. |
| V14 | C | Encrypted archive checksum/decryption/listing verified by operator; actual isolated restoration not tested. |
| V15 | C | Live migration unexecuted, gated on restore evidence and explicit approval. |
| V16 | C | Production deployment unexecuted, gated on quality/security/capacity/continuity and explicit approval. |
| V17 | C | Latest candidate's real hosted acceptance unexecuted, dependent on approved deployment. |
| V18 | A / C | Portfolio/source presentation complete: default branch, README, installation, architecture, synthetic screenshots and limitations. Production-complete tag/claim withheld. |

## Verification boundary

Previously verified, reused because application code is unchanged:

- Local application candidate: **1,380 backend passed, 5 opt-in skipped, 2 subtests
  passed; 162 frontend passed**; lint, typecheck, build and API contract checks passed.
- GitHub backend/frontend CI passed at `30d7c35` and `1d37c46`.
- V03/V10 focused run: **29 passed, 2 skipped, 2 subtests passed**; temporary-directory
  permission errors resolved with a workspace-local basetemp. Separate fresh 111-input
  Torch/ONNX comparison passed. No representative quality pass is asserted.
- Sanitized screenshots: built existing UI, synthetic example.invalid fixtures,
  no real Gmail/API data; page errors, hosted capability links, overflow and visual
  checks recorded in [gallery provenance](../portfolio/README.md).

Final pass checks are bounded to publication and documentation: clean starting branch
and expected history; remote/default-branch identity; pending-file size/type and
secret/private-data pattern review; local documentation targets/README anchors and
screenshot files; `.env.example` placeholders; evidence JSON consistency; staged
whitespace and docs-only scope; normal non-force push; remote HEAD equality; GitHub
backend/frontend workflow completion. No local application suite, model evaluation,
backup verification or infrastructure audit is repeated. Exact final CI results are
reported in the handoff and retained by GitHub on the published commit.

No model weights, personal datasets, mailbox messages, tokens or encrypted backups
are published by this pass. Pattern checks and focused review have limits; they are
not a formal security audit. The default-branch README explicitly discloses that
local models and Google credentials require provisioning and a clean clone is not
a turnkey hosted deployment.

## Genuine remaining production blockers

1. **Classifier quality/approval:** freeze an explicitly selected artifact and a
   separate representative human-reviewed holdout; run the existing one-time gate
   with unchanged coverage and thresholds. Do not recycle development examples.
   Any classifier-improvement or contract change requires separate scope approval.
2. **Security:** coordinate rotation of the exposed `inboxnizer_beta_db_user` password
   and protected dependent clients in an approved maintenance window. Verify actual
   runtime privileges, HTTPS/session/proxy/logging controls. The operator confirms
   temporary external IP access removal; do not reopen that completed item.
3. **Recovery:** restore the verified encrypted archive into a separate isolated
   database and verify schema, counts, constraints, checkpoints and key-based
   credential decryption. Archive listing is not restore proof; never publish keys.
4. **Host capacity and continuity:** obtain real target-host bounded-sync/concurrent
   Inbox memory/latency evidence and resolve the recorded Free PostgreSQL expiry
   (21 November 2026) without assuming a paid upgrade or migration authorization.
5. **Activation and real acceptance:** only after prerequisites pass, separately
   approve the exact migration/deployment described in the runbook and perform V17.
   The operator reports live Render remains `f53e22c`, auto-deploy disabled.

These blockers prevent production GO, not truthful portfolio presentation. No optional
feature or redesign is required to close this source release. This execution stops at
publication; it does not begin another development or deployment phase.
