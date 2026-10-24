> Historical local development report, preserved from the accessible workspace. Its results are not new verification or a claim of production readiness. See ../../README.md for current setup and ../VALIDATION.md for this update.

# Deeper quality evaluation — 2026-10-12

## Scope and decision

Ask changes are implemented locally. The classifier is an evaluated candidate, NOT the deployed classifier. No production reclassification, backfill, schema change, task-extraction change, frontend change, staging, commit or push was performed. Real mailbox evaluation used PostgreSQL SET TRANSACTION READ ONLY and OwnedSession.

Neither system is approved for bulk production reprocessing on this evidence alone. Ask request-time behavior improved; classification needs independently labelled representative mailbox evaluation before deployment. Existing stored predictions remain unchanged.

## Root causes and implementation

- The fact resolver previously answered conversational travel questions with one scalar. It now adds independently proved, non-conflicting fields from the same email/chunk/record. Explicit scalar questions remain scalar. Persisted optional fields use a bounded role vocabulary; no city, sender, airport, email ID or date is inferred.
- A booking header may precede an itinerary record. Inheritance requires a containing persisted header, provenance, and one unique booking reference in the entire owned document. Multiple references suppress the optional reference. Return-leg times are never merged into the selected leg.
- Application, event and bill answers can include supported labelled details from the record containing the extractive proof. Conditional optional values are skipped. Citation validation and source_supported/generated_synthesis warnings are unchanged.
- Recent intent formerly searched historical evidence without a message-time bound. Both vector and fact candidate SQL now constrain coalesce(message_at, sent_at), excluding unknown dates. Today/yesterday/calendar week/calendar month and rolling two weeks are supported. Clearly conversational/current status questions default to 14 days. Calendar boundaries use UTC, weeks start Monday; the answer discloses the period. Travel/event date questions do not mistake message timestamp for event date.
- Conversational Arabic status intent uses normalized tokens, source qualifiers and domain constraints. Literal complete acceptance/rejection sentences preserve polarity and conditions; missing evidence is explicitly not proof of rejection. Multiple applications clarify. Recency breaks status ties only when explicit application reference AND organization match, with reliable timestamps.
- Production classification uses an English DistilBERT checkpoint and always emits a top category. Prior audit found no Arabic in the 2,105-row public source, placeholders, duplicate conflicts, and professional/finance hard-negative gaps. Sigmoid maxima are not calibrated certainty. Stronger bilingual representations plus contrasting training examples address data and representation rather than sender rules.

## Training and evaluation discipline

- Frozen local multilingual-e5-small, normalized 512-token embeddings, balanced one-vs-rest logistic heads; no paid API. Production model is untouched.
- Existing grouped public split retained: 1,672 train / 214 validation / 217 diagnostic test. Contradictory duplicate rows were quarantined by the existing audited splitter.
- Added bilingual professional, finance, promo, personal, newsletter and application contrasts. Prior 20-case test is explicitly consumed development data now.
- Nine candidates (C=1/10/100, supplemental weights=1/3/6), seed 42; chosen on public validation + consumed development macro F1. Selected C=10, weight=3.
- NEW 40-case, class-balanced bilingual challenge was authored separately before training and used only after selection. No post-test tuning. Hash partitions are recorded in manifest.json. This small authored challenge is not a representative production gold set.

## Classifier results: new 40-case challenge

| Model | Accuracy | Macro F1 | Finance false positives | Wrong with confidence ≥0.8 | ECE |
|---|---:|---:|---:|---:|---:|
| production | 32.5% | 0.3624 | 5 | 5/40 | 0.3096 |
| previous-candidate | 82.5% | 0.8213 | 0 | 0/40 | 0.1662 |
| new-candidate | 92.5% | 0.9260 | 0 | 0/40 | 0.1555 |

Public diagnostic test (217 examples): previous candidate accuracy 88.02%, macro F1 0.6493; new candidate 87.56%, macro F1 0.6438. Finance false positives 0 → 1 and wrong high-confidence predictions 22 → 24. This regression blocks a blanket reliability claim. The old production checkpoint may have seen public examples, so this split is not a clean estimate of its generalization.

### New challenge per-class precision / recall / F1

| Class | Production P/R/F1 | Candidate P/R/F1 | Support |
|---|---|---|---:|
| Business | 0.10/0.50/0.16 | 1.00/0.75/0.86 | 4 |
| Customer Support | 0.00/0.00/0.00 | 1.00/1.00/1.00 | 4 |
| Events & Invitations | 1.00/0.25/0.40 | 1.00/0.75/0.86 | 4 |
| Finance & Bills | 0.29/0.50/0.36 | 1.00/1.00/1.00 | 4 |
| Job Application | 1.00/0.50/0.67 | 0.67/1.00/0.80 | 4 |
| Newsletters | 0.50/0.25/0.33 | 1.00/1.00/1.00 | 4 |
| Personal | 1.00/0.25/0.40 | 0.80/1.00/0.89 | 4 |
| Promotions | 1.00/0.25/0.40 | 1.00/1.00/1.00 | 4 |
| Reminders | 1.00/0.25/0.40 | 1.00/0.75/0.86 | 4 |
| Travel & Bookings | 0.50/0.50/0.50 | 1.00/1.00/1.00 | 4 |

Remaining challenge errors: Arabic professional banking discussion → Job Application; Arabic unfinished-survey reminder → Job Application; English volunteer gathering → Personal. Finance confusion improved, but occupational words still confuse Business and Job Application. Probabilities are not calibrated; ECE is diagnostic, not a guarantee.

## Read-only real Ask before / after

| Question | Before | After | After LLM calls |
|---|---|---|---:|
| متى رحلتي لجدة؟ | answered / deterministic_fact / 1 facts | answered / deterministic_fact / 6 facts | 0 |
| متى ب اسافر لجده؟ | answered / deterministic_fact / 1 facts | answered / deterministic_fact / 6 facts | 0 |
| متى رحلتي لجدة؟ (selected email) | answered / deterministic_fact / 1 facts | answered / deterministic_fact / 6 facts | 0 |
| انقبلت بمعسكر؟ | answered / generated_synthesis / 0 facts | insufficient_evidence / None / 0 facts | 0 |
| جاني قبول قريب؟ | insufficient_evidence / None / 0 facts | insufficient_evidence / None / 0 facts | 0 |
| وش صار على طلباتي آخر أسبوعين؟ | insufficient_evidence / None / 0 facts | insufficient_evidence / None / 0 facts | 0 |
| هل وصلني شيء جديد من الجامعة؟ | insufficient_evidence / None / 0 facts | insufficient_evidence / None / 0 facts | 0 |
| وش آخر تحديث على طلبي؟ | insufficient_evidence / None / 0 facts | insufficient_evidence / None / 0 facts | 0 |
| What is the submarine booking number? | insufficient_evidence / None / 0 facts | insufficient_evidence / None / 0 facts | 1 |

Actual selected travel answer:

موعد رحلتك: 16-Oct-2026 (2026-10-16)؛ وقت المغادرة: 11:35؛ وقت الوصول: 13:25؛ المغادرة من: الرياض؛ الوجهة: جده؛ رقم الحجز: KI76YH. [email_id=4]

Both unscoped Arabic travel paraphrases also returned the same six supported fields without the LLM. The old answer had one date field. No airport names were guessed. Unsupported submarine query still abstains.

Five recent/status real queries abstained within the explicit recent window. These are not labelled false-abstention measurements: the mailbox lacks an independently adjudicated acceptance/status gold set. Do not interpret five abstentions as five accurate negative answers. Generic isolated-database tests prove positive acceptance, explicit rejection, temporal exclusion, clarification and same-application latest-status behavior. They do not establish production recall.

## Tests and limits

27 new regressions in test_ask_deeper.py cover SQL time windows, same-record bundles, parent booking uniqueness, multiple itineraries, literal positive/negative status, conditional status, ambiguous applications, tenant isolation, unknown timestamps, event details, finance details, no invented airports, Gulf departure phrasing, and training/challenge separation.
Full suite result recorded in results/quality-deeper-20261012/full-tests.log. Relevant tracked diff check passed. Whole-tree git diff --check still reports pre-existing unrelated trailing whitespace at test_main.py:37; it was not modified.

- Recent general activity without a recognized status sentence can still abstain. This is not unrestricted mailbox reasoning.
- Optional details require persisted supported labels/record boundaries. Missing or ambiguous fields are omitted; no re-extraction/backfill ran.
- A unique booking header remains a conservative document-level association, not a general proof of arbitrary cross-record relationships.
- Time defaults use UTC and 14 days; explicit older application questions and locale-specific week boundaries need further product coverage.
- The 40 authored cases are consumed after this report; future model selection needs a fresh holdout. No post-result tuning was performed.
- Generated synthesis remains explicitly unverified; no general semantic entailment model was added.

## Exact files changed in this task

Production: rag_service.py, rag_retrieval.py, rag_candidates.py, rag_extractive.py, question_understanding.py; new rag_time.py, rag_status.py, rag_bundle.py.
Tests/tooling: test_ask_deeper.py; quality/deeper_cases.py, quality/deeper_classification.py, quality/deeper_mailbox.py.
Documentation: DEEPER_QUALITY_REPORT.md.
Ignored local artifacts: results/quality-deeper-20261012/ (baseline snapshots, partition hashes, classifier candidate, metrics, read-only Ask comparisons and test logs). No private email bodies were copied into tests or reports.
