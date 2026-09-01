# Phase 5.1 evaluation integrity audit

## Scope and frozen Benchmark A

Benchmark A is the **Specification Benchmark**: 120 cases, seed 42, 12 in each of the original ten categories. The generator, original evidence dataclasses, ground-truth semantics and single-payment reconciliation rules are unchanged. Its canonical dataset SHA-256 remains `817f2fe2fa3828a275b2596e81dd1d2186f021ca036e34d3c721ca205ff861ce`, pinned by a regression test. Run metadata now identifies the benchmark; this does not alter the dataset hash.

Benchmark B is the separate **Robustness Suite**: 36 independently authored cases, seed 314159, two variants of 18 scenarios. It neither imports nor calls A's generator. The same metric implementation scores both independently; no combined headline score is produced. Neither is an independently collected production holdout. Both remain developer-authored synthetic specification/robustness tests, and engine improvements were informed by B's results.

## Coupling findings

| Audit area | Finding |
| --- | --- |
| Labels and reasons | The engine receives records and a case ID, never the Case's expected classification/reason. Classification enum/status mapping is a shared output vocabulary, not a per-case label oracle. |
| IDs and construction order | **Latent leakage in A:** contiguous category-sized construction blocks produce IDs from which category can be inferred, even after shuffling. Engine does not parse IDs. A is frozen, so this is disclosed rather than silently renumbered. B uses independently randomized case/record IDs. |
| Import boundary | Both decision modules import evidence schemas, not either generator/evaluator. Fresh-process tests enforce this. No AI, database or configuration dependency exists in decision modules. |
| Shared helpers | Generators do not call decision rules. A creates a consistent ledger baseline and introduces labelled changes. B authors separate scenarios. This is co-design, not statistical independence; high A accuracy is expected for specification conformance. |
| Sentinel/template cues | Some shapes strongly correlate with labels by construction: missing records, capture failure, currency contradiction, incomplete snapshots. These are semantic evidence, not special magic strings read by the engine. Amount ranges and refund templates are narrow and not representative prevalence samples. |
| Ordering | A accepts one payment, not a full attempt history. Its shuffle cannot establish attempt-selection correctness. B permutes attempts/refunds/orders and swaps primary/other attempt positions in tests. |
| Identity/types | No object identity or expected-category-specific Python type drives a classification. B has a richer workflow input schema because it carries collections, not because a type denotes a category. |
| Metadata | Human descriptions/optional timestamps/method labels are not required. B's optional metadata is stripped from decision/audit evidence; poisoning it with an expected label does not change prediction. |
| Operational fields | Lookup completeness, due status, reported refunded amount and documented fee/adjustment inputs are plausible imported-ledger facts, but **not automatically present or established by current operational tables**. Production adapters must prove completeness and deadlines. No automatic reliable-default claim is made. |

## Robustness scenarios and realism

Each has two cases: failed-then-captured; similar records with different references; wrong-reference same-amount; partial refund; multiple refunds; refund overflow plus settlement variance; documented fees; documented adjustments; unexplained one-paise variance; absent/irrelevant optional metadata; missing relationship; contradictory capture flag; missing payment plus missing settlement; failed/pending order with amount difference; boundary amounts; amount mismatch before missing settlement; split captures; conflicting duplicate capture IDs.

B ground-truth distribution: MATCHED 17; PAYMENT_FAILED 2; AMOUNT_MISMATCH 2; MISSING_PAYMENT 2; REFUND_MISMATCH 2; SETTLEMENT_VARIANCE 2; UNRESOLVED 9. Categories without B cases remain represented by A and are not assigned fabricated recall denominators.

The variants include INR 1, invalid zero capture, INR 10 lakh, partial/multiple refunds, documented integer fee rounding and one-paise deltas. Same-amount records are joined by IDs, never amount. Optional shared timestamps are non-semantic context, not chronology evidence. The successful capture supersedes a failed attempt because it proves funding, not because it is last in a list. Both attempts remain in output evidence.

Split captures represent two distinct partial payments funding one paid order. Their labels remain MATCHED because the complete supplied amounts sum to the order. Current PayOps single-payment reconciliation does not aggregate them. They are retained as measured unsupported cases, not relabelled UNRESOLVED to improve scores.

## Failure analysis before fixes

The old engine cannot consume B's collections/flags. A diagnostic projection of B onto its single `snapshot` input scored **28/36**, with eight mismatches. This projection intentionally exposes the old model's limits; it is not equivalent to evaluation of the complete B input.

| Cases | Initial failure | Assessment and action |
| --- | --- | --- |
| B-301708, B-634768 | Failed attempt selected despite available capture | DATA MODEL LIMITATION: add evidence-only attempt selection, keeping failed attempt in audit evidence. |
| B-277565, B-451866 | Captured status matched despite false capture flag | DATA MODEL LIMITATION / unsafe ignored contradiction: add flag consistency validation in the richer evidence adapter. |
| B-457111, B-627804 | Conflicting snapshots with one ID ignored | DATA MODEL LIMITATION: refuse duplicate identity without version/deduplication evidence. |
| B-315412, B-676861 | Partial capture compared individually with whole order | UNSUPPORTED EDGE CASE: keep expected MATCHED, return UNRESOLVED until split allocation is supported. |

No ambiguous ground-truth label was rewritten. A's original rules were not tuned. The new workflow adapter delegates selected, complete single-payment evidence to those unchanged rules. Explicitly contradictory or unsupported collection evidence is rejected before delegation.

## Precedence

Workflow identity/duplicate/capture contradictions precede selection. A single relevant successful payment can supersede terminal failures; multiple captures or other non-final attempts remain unresolved. Unrelated records never match merely because their amounts agree. After selection, A's precedence applies: lookup completeness/relationships → missing payment → terminal failure → captured amount → order confirmation → refunds → settlement. Thus failed/pending-order precedes amount matching; refund overflow precedes settlement variance; no payment precedes missing settlement. One primary explanation is reported, not an exhaustive list of all anomalies.

## Final measured classifications

| Metric | A | B |
| --- | --- | --- |
| Exact classifications | 120/120 (100%) | 34/36 (94.44%) |
| Clean-match recall | 12/12 (100%) | 15/17 (88.24%) |
| Exception precision / recall / F1 | 100% / 100% / 100% | 100% / 100% / 100% |
| Exact exception classification / actual exceptions | 96/96 | 10/10 |
| Predicted unresolved | 12 (10%) | 11 (30.56%) |
| Correctly / incorrectly unresolved | 12 / 0 | 9 / 2 |
| False positive / missed exceptions | 0 / 0 | 0 / 0 |
| Wrong exception types | 0 | 0 |

Every B mismatch: **B-315412 and B-676861**, expected MATCHED, predicted UNRESOLVED, unsupported split-capture aggregation. These reduce exact accuracy and clean recall. They are not binary missed exceptions because ground truth is clean. Correctly unresolved: B-871437 (zero capture), B-457111 and B-627804 (duplicate identity), B-277565 and B-451866 (capture contradiction), B-293402/B-262429/B-400776/B-374171 (wrong/missing relationship). Full reasons/evidence are in generated JSON.

Runtime/throughput are measured per invocation with perf_counter, never fixed scores. They cover local in-memory generation/hash/reconciliation/report work, not network, API, LLM, printing or file I/O. B adds adapter overhead; do not compare either with infrastructure capacity.

## Running and verification

```powershell
python -m app.evaluation.run --benchmark specification --json
python -m app.evaluation.run --benchmark robustness --json
```

The original command still runs A with seed 42. B defaults to 314159. Optional `--seed` overrides either. A writes ignored `generated/evaluation/latest.json`; B writes ignored `generated/evaluation/robustness.json`. Metadata identifies the suite/version/seed/hash. No benchmark is sent to OpenAI.

Integrity tests cover frozen A hash, label/case-ID/description poisoning, case and record permutations, optional metadata stripping, primary attempt position, referential ID renaming, monetary/reference sensitivity and repeatable serialized reports excluding timing. The SQL isolation test runs both suites and asserts no statements plus identical operational test rows. Live PostgreSQL availability is reported separately; unavailable live counts are not claimed as verified.

Remaining limitations: trusted input/completeness assertions; no general multi-capture or batch allocation; conservative duplicate handling without version history; no FX, chargebacks or tax/fee inference; primary issue rather than multi-label diagnosis; no independent external holdout. Deterministic correctness is distinct from AI-assisted explanation. Phase 6 now presents these frozen results but does not change or rescore them.
