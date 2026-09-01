# PayOps AI

PayOps AI is a payment-operations copilot for businesses using Razorpay. Phase 4 adds controlled, read-only LLM reasoning over the existing PostgreSQL analytics and normalized payment records.

> **Razorpay Live Mode: NOT IMPLEMENTED.** PayOps AI is advisory and read-only: it cannot capture, refund, settle, resolve, or move money.

## Architecture

- **Frontend:** Next.js App Router, TypeScript, Tailwind CSS
- **Backend:** FastAPI, SQLAlchemy, Pydantic
- **Database:** PostgreSQL 16 for local development
- **Local orchestration:** Docker Compose for PostgreSQL

See [docs/architecture.md](docs/architecture.md) for the planned future data flow.

## Repository structure

```text
payops-ai/
├── frontend/       # Next.js dashboard
├── backend/        # FastAPI application and tests
├── database/       # Database notes and future migrations
├── docs/           # Architecture documentation
├── AGENTS.md
├── .env.example
├── docker-compose.yml
└── README.md
```

## Prerequisites

- Node.js 20 or newer and npm
- Python 3.11 or newer
- Docker Desktop with Docker Compose

## Local development

### 1. Configure environment variables

Copy `.env.example` to `.env` at the repository root. The included development defaults align with Docker Compose. Never commit `.env`.

For Razorpay Test Mode, configure `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` locally. Test keys begin with `rzp_test_`. Configure `RAZORPAY_WEBHOOK_SECRET` only after creating a webhook endpoint in the Razorpay dashboard. Never use Live Mode credentials in this project phase.

For PayOps AI, configure `OPENAI_API_KEY` and optionally `OPENAI_MODEL` (default: `gpt-5.4-mini`). Secrets remain backend-only and must never be placed in frontend environment variables.

### 2. Start PostgreSQL

```bash
docker compose up -d postgres
docker compose ps
```

The database is available at `localhost:5432`, with database, user, and password all set to `payops` for local development only.

### 3. Apply migrations and seed demo data

```bash
cd backend
python -m venv .venv
# activate the environment as shown below, then:
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
```

The seed is deterministic and safe to rerun. It replaces only the named demo merchant dataset, preventing duplicate records.

To reset/reseed development data, run:

```bash
cd backend
alembic downgrade base
alembic upgrade head
python -m app.seed
```

The downgrade command deletes Phase 2 tables and their development data. For a non-destructive refresh, run only `python -m app.seed`.

### 4. Start FastAPI

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/health` or API documentation at `http://localhost:8000/docs`.

To explicitly validate PostgreSQL connectivity after starting the service:

```bash
cd backend
python -c "from app.database import check_database_connection; print(check_database_connection())"
```

### 5. Start Next.js

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The server-rendered Overview page requests its data from `BACKEND_URL` (default: `http://localhost:8000`). Start the API before loading the page.

## Phase 2 functionality

- Relational merchant, customer, order, payment, refund, settlement, alert, and reconciliation models
- Alembic-managed PostgreSQL schema
- Repeatable 248-payment demo dataset with UPI failures, settlement discrepancy, refunds, and reconciliation mismatches
- PostgreSQL-backed summary, volume series, and payment-method analytics for 1D/7D/30D periods
- Functional Overview, Payments, Settlements, Reconciliation, and Alerts pages
- Payment status/method/search filters and simple limit/offset pagination
- Payment source filtering with `source=all` (default), `source=demo`, or `source=razorpay`; detail lookup accepts a local ID or external payment ID
- Source-aware dashboard analytics use the same `source=all|demo|razorpay` contract. The Overview defaults to All Data and never performs a remote sync while rendering.
- CORS configured for the local frontend origin
- Backend scenario, analytics, API filter, monetary, and seed-idempotency tests

## Phase 3A: Razorpay Test Mode foundation

All Razorpay HTTP access is isolated under `backend/app/integrations/razorpay`. Requests use HTTP Basic authentication, bounded counts, explicit timeouts, and sanitized custom exceptions.

Verify the configured read-only connection:

```bash
curl http://localhost:8000/api/integrations/razorpay/status
```

Manually synchronize at most 25 recent entities per resource:

```bash
curl -X POST "http://localhost:8000/api/integrations/razorpay/sync?count=25"
```

Sync is never run during application startup. It upserts by Razorpay external IDs and uses a dedicated local merchant whose `source` is `razorpay`; seeded records remain attached to the `demo` merchant and are not deleted or merged.

Dashboard summary, volume, payment-method, issue, settlement, alert, and reconciliation reads accept the same source values. Razorpay-only views return zero or an empty list when no local settlement, alert, or reconciliation record exists; the application does not fabricate operational records.

### Webhooks

The receiver is `POST /api/webhooks/razorpay`. It reads the original request bytes, verifies `X-Razorpay-Signature` with HMAC-SHA256 and `RAZORPAY_WEBHOOK_SECRET`, then persists the unique `x-razorpay-event-id` before applying an entity upsert. Missing configuration and invalid signatures fail closed.

Supported events are `payment.authorized`, `payment.captured`, `payment.failed`, `order.paid`, `refund.created`, and `refund.processed`. Valid unsupported events are recorded and safely acknowledged.

A public HTTPS endpoint is required before Razorpay can deliver webhooks to a local development machine. Creating a tunnel and configuring the resulting webhook URL in the Razorpay Test Mode dashboard remain manual steps; this application does not create dashboard webhooks automatically.

```text
Razorpay Test Mode
      ↓
Public HTTPS/tunnel URL
      ↓
POST /api/webhooks/razorpay
      ↓
Raw-body signature verification
      ↓
Unique event-ID check
      ↓
Shared entity upsert
      ↓
PostgreSQL
```

## Phase 4: controlled PayOps AI

PayOps AI uses the OpenAI Responses API with strict custom function tools. The model never receives a database connection, SQL capability, Razorpay credentials, or mutating functions. It selects from a static dispatcher of approved backend tools, receives structured results, and produces an evidence-based explanation.

Available tools:

- Dashboard summary
- Payment failure statistics and reason breakdown
- Failure-rate comparison
- Bounded failed-payment facts
- Settlement variance
- Reconciliation issues
- Recorded alerts
- Normalized payment details

The conversation endpoint is:

```text
POST /api/copilot/query
```

Example request:

```json
{"message":"Why are UPI payments failing today?","source":"demo"}
```

The response contains the answer, selected source, tools used, and concise evidence labels. Tool calls are capped at six rounds. The normal test suite mocks OpenAI and does not require internet access.

To test manually, start PostgreSQL, FastAPI, and Next.js, open `/copilot`, select a source, and use one of the starter questions. The Overview source is inherited when opening PayOps AI from its dashboard panel.

Privacy boundary: tool outputs are bounded and purpose-specific. Customer email and phone are never sent to the model; only a customer name is included when necessary for failed-payment or reconciliation questions. Complete payloads and hidden prompts are not logged.

## Phase 5: offline reconciliation benchmark

From `backend`, run `python -m app.evaluation.run --seed 42 --json` to evaluate 120 deterministic synthetic cases. No operational database or OpenAI access is required. Results include exact classifications, exception metrics, unresolved evidence and an ignored JSON report. See [benchmark documentation](docs/evaluation.md) for ground truth, denominators, isolation and limitations. This measures local synthetic reconciliation, not production capacity or universal accuracy.

Phase 5.1 adds a separate robustness audit: `python -m app.evaluation.run --benchmark robustness --json`. Benchmark A remains frozen. See [evaluation integrity findings](docs/evaluation-integrity.md) for the separate scores and retained unsupported cases.

## Deferred features

- Authentication and authorization
- Razorpay Live Mode and production account linking
- Automated webhook/tunnel configuration
- Advanced anomaly detection
- Refund, settlement, or payment actions
- Autonomous financial actions or approval workflows
- Production deployment and observability
