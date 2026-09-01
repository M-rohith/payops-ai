# Phase 5: reconciliation benchmark

The original suite is now **Benchmark A — Specification Benchmark**, frozen unchanged. Phase 5.1 adds separate **Benchmark B — Robustness Suite** and an evidence adapter for multiple attempts; see [integrity audit](evaluation-integrity.md) for leakage findings, retained failures, results and CLI commands. Scope descriptions below refer to A's original single-payment engine.

## Purpose and isolation

This offline benchmark measures deterministic reconciliation of synthetic payment-operations evidence. It does not measure the LLM or the existing API's stored reconciliation issue feed. The existing feed has no matching engine to extract; operational APIs, SQLAlchemy models, Razorpay and Copilot remain unchanged.

`backend/app/evaluation/` uses standard-library immutable dataclasses and explicit in-memory records. It does not import database configuration, SQLAlchemy, OpenAI, or the AI agent. It performs no network calls and never seeds operational tables. JSON output supports offline audit, while the `/evaluation` page consumes a cached, presentation-safe API projection computed in memory.

## Running

From `backend` with the virtual environment active:

```powershell
python -m app.evaluation.run
python -m app.evaluation.run --seed 42 --json
```

`--json` writes/overwrites `backend/generated/evaluation/latest.json`, an ignored generated artifact. It contains metadata, dataset hash, metrics, confusion matrix, all cases with evidence/ground truth, error cases and unresolved cases. No output file is written by default. Ratios are JSON numbers in [0,1], or `null` when their denominator is zero. The CLI formats ratios as percentages or N/A. Runtime is deliberately not reproducible; all other report fields are reproducible for the same implementation and seed.

## Dataset and ground truth

Version 1.0 uses seed **42**, local `random.Random`, stable synthetic identifiers, integer INR paise and no wall-clock-dependent data. There are **120 cases: 12 each** of MATCHED, PAYMENT_FAILED, AMOUNT_MISMATCH, ORDER_NOT_CONFIRMED, MISSING_PAYMENT, MISSING_ORDER, REFUND_MISMATCH, MISSING_SETTLEMENT, SETTLEMENT_VARIANCE and UNRESOLVED. This gives 12 clean, 96 exception and 12 deliberately unresolved cases.

Labels/reasons are authored by scenario construction, never obtained by calling the engine. The engine accepts only case ID and input evidence, not labels or ground-truth reasons. Hashing the canonical ordered dataset (including labels) produces an auditable SHA-256 identity. The labelled dataset and engine are co-designed specification tests, not an independently collected holdout set.

Records reuse existing names: paid/created/attempted orders, captured/failed/authorized payments, processed/failed refunds and processed settlements. Benchmarked settlement records represent a **single-payment allocation**, not a claim that the current operational schema stores payment-level settlement membership. Benchmark-only evidence includes lookup completeness, settlement due status, fees/adjustments and a payment's reported refund total. These facts would require trustworthy reports and settlement-calendar policies in a real adapter; the benchmark does not invent a universal settlement SLA.

Variants cover partial refunds, failed refunds incorrectly reported as processed, over-refunding, positive/negative adjustments, under/over-settlements, unknown settlement eligibility, incomplete lookups, non-final authorization and contradictory references/currencies. Amount mismatch cases intentionally select the upstream amount discrepancy before evaluating any downstream settlement inconsistency.

## Rules and safe failure

The engine returns one primary explanation, with this precedence: order/payment snapshot completeness and identity; missing records; final payment status; amount comparison; order confirmation; refund evidence; settlement eligibility and net comparison. A known upstream issue can be returned without resolving downstream evidence. Contradictions that prevent the relevant comparison return UNRESOLVED, rather than invented financial causes.

Processed refunds alone contribute to refund totals. Pending refunds, duplicate refund IDs or unknown/misaligned references remain unresolved. A refund total above capture or inconsistent with the payment summary is REFUND_MISMATCH. Expected net is calculated as `captured amount - processed refunds - fees + signed adjustments`. Declared expected net must agree with that calculation; if not, the evidence is contradictory and unresolved. Actual minus expected is the same variance direction used by existing settlement APIs. Missing settlement requires both explicit due status and complete settlement lookup. No settlement before it is due is not an exception.

## Metrics and denominators

An **exception** is any of the eight labels other than MATCHED and UNRESOLVED. Unresolved is neither an exception nor a clean match.

| Metric | Definition |
| --- | --- |
| Cases processed | Number of cases evaluated, not count of underlying records |
| Clean-match recall | Correctly predicted MATCHED / ground-truth MATCHED |
| Exception precision | Predictions that are exceptions and whose ground truth is also an exception / all predicted exceptions |
| Exception recall | Same true exception detections / all ground-truth exceptions |
| Exception F1 | 2TP / (2TP + FP + FN); zero if denominator exists but TP is zero |
| Exception classification accuracy | Correct exact exception labels / all ground-truth exceptions; missed/abstained exceptions count as wrong; ground-truth UNRESOLVED is excluded |
| Overall correctness | Exact classification matches / all cases; correct UNRESOLVED counts as correct |
| Unresolved rate | Predicted UNRESOLVED / all cases |
| Unresolved precision / recall | Correctly unresolved / predicted unresolved; correctly unresolved / ground-truth unresolved |

False positive exceptions include predictions on either genuinely clean or unresolved cases. Missed exceptions include true exceptions predicted as MATCHED or UNRESOLVED. Wrong exception categories count as binary true detections but as misclassified types and incorrect exact classifications. Incorrectly unresolved means predicted UNRESOLVED with any other ground truth. The confusion matrix preserves every expected/predicted category combination.

Runtime uses `time.perf_counter()` around generation, canonical dataset hashing, reconciliation, metrics and report assembly. It excludes interpreter/import startup, printing and JSON file I/O. Throughput is cases divided by this total local in-memory runtime, **not network/API/production throughput**.

## Validation and limitations

Tests cover all category variants, reproducibility, independent intentionally-wrong prediction fixtures, undefined/zero metric denominators, label poisoning, safe failure and a fresh-process import boundary. A seeded in-memory operational database is snapshotted before and after evaluation and a SQL execution listener asserts zero evaluation SQL statements. Live PostgreSQL count checks are supplementary, not required to run the benchmark.

Synthetic benchmark accuracy does not imply universal production accuracy. This is a small, balanced specification benchmark, not a representative estimate of real incident prevalence. It excludes multi-attempt aggregation, split captures, cross-currency conversion, chargebacks, multi-payment settlement batches, taxes beyond supplied fees, asynchronous snapshot ordering and negative-net carry-forwards. It returns a primary issue, not an exhaustive multi-label diagnosis. Inputs are trusted typed benchmark structures, not a public ingestion API. No probabilistic confidence is claimed.

The judge-facing `/evaluation` UI displays metrics and summarized evidence through `GET /api/evaluation`. No evaluation persistence, live-data adapter, AI scoring, or financial action is implemented.
