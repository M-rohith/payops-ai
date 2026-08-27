# PayOps AI Architecture

## Phase 4

The implementation contains the source-aware payment analytics stack, Razorpay Test Mode ingestion, and a controlled PayOps AI layer. The AI agent uses the OpenAI Responses API with strict custom tools and a static dispatcher. Each tool calls approved SQLAlchemy analytics/services; the model has no direct database or Razorpay access.

Demo and Razorpay data are separated by merchant source: the deterministic merchant uses `demo`, and a single MVP integration merchant uses `razorpay`. Full multi-tenant OAuth/account linking is intentionally deferred.

## Planned future data flow

```text
Razorpay Test Mode               [Phase 3A bounded reads/webhooks]
   ↓
Read APIs + Verified Webhooks    [Phase 3A]
   ↓
FastAPI Backend                 [Phase 2 APIs]
   ↓
PostgreSQL                      [Phase 2 demo schema and data]
   ↓
Analytics / Reconciliation      [Phase 2 foundational analytics]
Anomaly Detection               [not implemented]
   ↓
Controlled PayOps AI Tools      [Phase 4 read-only]
   ↓
Responses API Reasoning         [Phase 4]
   ↓
Next.js Dashboard               [Phase 2 operational pages]
```

## Design boundaries

Business calculations belong in backend services. The frontend consumes API responses and focuses on presentation. When AI support is added, the LLM will operate through narrow, auditable backend tools rather than receiving unrestricted database access.

All money is stored as integer minor units (paise for INR). This avoids floating-point errors in payment, refund, and settlement calculations.

**Razorpay Live Mode and production account linking: NOT IMPLEMENTED.**

PayOps AI is strictly advisory. No capture, refund, settlement, alert-resolution, reconciliation mutation, or other money-moving tool is exposed. Structured evidence remains in integer minor units; only the final human-facing answer formats rupees.
