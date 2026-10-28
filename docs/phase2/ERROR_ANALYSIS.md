# Validation error analysis

This is analysis of actual Phase 2 validation predictions, not new labels or a
human-reviewed accuracy benchmark. Raw texts, row identifiers and predictions stay
in ignored local results. Examples below are intentionally short paraphrases of
reviewed public-source errors; they are not additional training data.

## Observed patterns

- **Newsletter versus promotion:** A has four `Newsletters -> Promotions` errors;
  B has three and C four. Reviewed examples announce a sale or offer a purchase
  discount while the reference label is only Newsletters. Marketing intent and
  recurring-message format overlap. These are plausible annotation ambiguities;
  no reference label was changed to improve the measured score.
- **Billing versus support:** A has four `Finance & Bills -> Customer Support`
  errors, B one and C five. A reviewed example describes a delayed purchase and
  directs the recipient to a support team, without a substantive billing action.
  A related example carries Finance & Bills plus Personal labels with similar
  order-delay content. Taxonomy guidance is needed before treating every mismatch
  as either model failure or annotation failure.
- **Personal/promotion versus support:** a reviewed order-delay notification is
  annotated Personal plus Promotions; all three approaches include this error
  pattern. Template overlap and weak labels can reward superficial wording.
- **Business/event ambiguity:** A has three Business + Events & Invitations to
  Personal errors. C has four Business + Events & Invitations to Newsletters errors.
  These aggregate patterns need independent human review; no new ground truth is
  asserted from the predicted label.

Full pattern counts, per-class precision/recall/F1/support, calibration bins and
fractional confusion matrices are generated from the stored validation outputs in
`evidence/`. Qualitative observations do not remove examples or alter those metrics.

## Consequences

A lower error count on this corpus is not proof of useful mailbox generalization.
Template grouping reduces leakage but cannot recreate missing sender/thread history
or repair uncertain labels. Keep the source's actual provenance, document uncertain
annotation rules, and human-review an independently sampled dataset before the
final quality gate. Do not turn these consumed validation examples into a test set.

Arabic and task-extraction error analyses are **not available**: no legitimate
Arabic/category or action/deadline gold was admitted. Existing fictional UI samples
and regression fixtures are not substitutes for those evaluations.
