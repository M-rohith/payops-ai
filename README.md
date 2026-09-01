# PayOps AI

**A read-only AI Finance Controller for payment operations that combines deterministic reconciliation with evidence-grounded AI investigation.**

Target track: **Track 04 — AI Finance Controller**, Razorpay Buildathon.

> PayOps AI uses Razorpay **Test Mode** and synthetic evaluation data. It is an advisory and investigation system: it cannot capture, refund, transfer, settle, or otherwise move money.

## The problem

Payment-operations teams often reconcile orders, payment attempts, refunds, and settlements across separate records. Failures, delayed states, missing references, and legitimate fees can look similar, making manual investigation slow and error-prone. An LLM-only approach is unsafe for financial arithmetic because it can invent conclusions. Finance teams need deterministic checks, explicit uncertainty, and an audit trail for every explanation.

## The solution

PayOps AI combines:

- Razorpay Test Mode API and signed webhook ingestion;
- a source-aware operations dashboard for Demo, Razorpay Test, or All Data;
- deterministic reconciliation over orders, payments, refunds, fees, adjustments, and settlements;
- an allowlisted read-only AI tool layer for evidence-backed investigation;
- `UNRESOLVED` safe failure when evidence is incomplete or contradictory; and
- two reproducible synthetic benchmarks with a judge-facing case audit at `/evaluation`.

The split is deliberate: **code decides financial classifications and arithmetic; AI selects controlled tools and explains structured evidence.** Benchmark correctness does not depend on OpenAI availability.

## Why it fits AI Finance Controller

PayOps AI demonstrates multi-source payment operations, settlement investigation, deterministic batch reconciliation, measurable exception precision/recall and local throughput, plus explicit unresolved cases. The Copilot complements those controls with grounded investigation; it does not replace them.

## Key differentiators

| Principle | Implementation |
| --- | --- |
| Deterministic financial correctness | Matching, refund aggregation, settlement arithmetic, precedence, and evaluation run in Python—not in an LLM. |
| Controlled AI access | The OpenAI model can call only nine allowlisted read-only backend tools through a static dispatcher. |
| Evidence grounding | Copilot answers show the selected source and friendly evidence/tool labels. |
| Source isolation | `demo`, `razorpay`, and `all` are explicit API/UI scopes; demo records are not merged with Razorpay records. |
| Safe failure | Missing or contradictory evidence produces `UNRESOLVED` rather than a fabricated explanation. |
| Auditable evaluation | Specification and robustness benchmarks remain separate, deterministic, inspectable, and reproducible. |

## Architecture

### Operational and AI path

```mermaid
flowchart LR
    R[Razorpay Test Mode] -->|API reads / signed webhooks| F[FastAPI]
    F --> P[(PostgreSQL)]
    P --> A[Analytics and operational reconciliation]
    A --> T[Allowlisted read-only tools]
    U[User question] --> O[OpenAI Responses API]
    O -->|function selection only| T
    T -->|structured evidence| O
    O --> C[PayOps AI Copilot]
    F --> D[Next.js operations dashboard]
```

### Independent evaluation path

```mermaid
flowchart LR
    S[Synthetic cases + labels] -->|financial evidence only| E[Deterministic reconciliation]
    S -->|ground truth retained by evaluator| V[Evaluator]
    E -->|predicted classification| V
    V --> M[Metrics and per-case audit]
    M --> UI[Evaluation UI]
```

Ground-truth labels are held by the evaluator and are **not** passed to the reconciliation engine. See [architecture details](docs/architecture.md), [metric definitions](docs/evaluation.md), and the [integrity audit](docs/evaluation-integrity.md).

## Technology stack

- **Frontend:** Next.js App Router, React, TypeScript, Tailwind CSS, native accessible SVG charts, `react-markdown`, `remark-breaks`
- **Backend:** Python, FastAPI, SQLAlchemy, Alembic, Pydantic
- **Database:** PostgreSQL 16
- **AI:** OpenAI Responses API, strict function/tool calling, static allowlisted dispatcher
- **Payments:** Razorpay Test Mode API, webhooks, raw-body HMAC signature verification, event idempotency
- **Infrastructure:** Docker and Docker Compose; zrok supported for local webhook tunnelling
- **Verification:** pytest, TypeScript compiler, ESLint, Next.js production build

Recharts is not a project dependency; the current volume chart is implemented directly with SVG.

## Evaluation results

These are **developer-authored synthetic benchmarks and are not independent production validation**. They measure deterministic reconciliation, not AI prose quality.

| Metric | Benchmark A — Specification | Benchmark B — Robustness |
| --- | ---: | ---: |
| Seed | 42 | 314159 |
| Cases | 120 (10 categories × 12) | 36 (18 scenarios × 2) |
| Exact correctness | 120/120 | 34/36 (94.44%) |
| Clean-match recall | 100% | 88.24% |
| Exception precision / recall / F1 | 100% / 100% / 100% | 100% / 100% / 100% |
| Exact exception classification | 100% | 100% |
| Predicted unresolved | 12 | 11 |
| Correctly / incorrectly unresolved | 12 / 0 | 9 / 2 |

The two Benchmark B mismatches are expected `MATCHED` split-capture cases predicted `UNRESOLVED`. General split-capture aggregation is not supported; the engine refused to guess instead of declaring a false match or exception. Open `/evaluation` to inspect metrics, distributions, filters, reasons, and summarized evidence for all 156 cases.

## Razorpay Test Mode integration

Razorpay credentials are loaded from environment variables. The webhook receiver at `POST /api/webhooks/razorpay`:

1. reads the original request bytes;
2. verifies `X-Razorpay-Signature` using HMAC-SHA256 and `RAZORPAY_WEBHOOK_SECRET`;
3. persists the provider event ID under a unique constraint for idempotency; and
4. upserts normalized order, payment, or refund records by external ID.

The handler does not assume webhook delivery order. Supported payment, order, and refund events can arrive more than once without creating duplicate normalized records. A real INR 100 Test Mode payment flow was validated locally. No Live Mode credential or resource is included.

For local delivery, run the API and expose it with an installed/enabled zrok client:

```powershell
zrok share public localhost:8000
```

Configure the resulting HTTPS URL plus `/api/webhooks/razorpay` manually in the Razorpay Test Mode dashboard. The URL is ephemeral; do not commit it. Refer to the official [zrok HTTP sharing guide](https://docs.zrok.io/docs/1.0/concepts/http/) for account/client setup.

## Controlled AI architecture

```text
User question
    ↓
OpenAI model
    ↓
Allowlisted function selection
    ↓
Read-only backend tool
    ↓
Structured payment evidence
    ↓
Grounded response with source and evidence labels
```

The model has no SQL tool, database connection, Razorpay credentials, refund/capture/transfer tool, or arbitrary code/database access. Tool calls are validated, source-scoped, bounded to six rounds, and return purpose-specific evidence. Customer email and phone are excluded from AI tool output. The ordinary test suite mocks OpenAI and requires no network access.

## Quick start

### Prerequisites

- Git
- Docker Desktop with Docker Compose
- Python 3.11 or newer
- Node.js 20 or newer with npm

### 1. Clone and configure

```powershell
git clone <repository-url>
cd payops-ai
Copy-Item .env.example .env
```

On macOS/Linux, use `cp .env.example .env`. The checked-in defaults configure local PostgreSQL. Add only the Test Mode and OpenAI secrets needed for the flows you plan to demonstrate. Never commit `.env`.

```dotenv
DATABASE_URL=postgresql+psycopg://payops:payops@localhost:5432/payops
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

### 2. Start PostgreSQL

```powershell
docker compose config --quiet
docker compose up -d postgres
docker compose ps
```

Wait for `payops-postgres` to report `healthy`.

### 3. Install, migrate, and seed the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m app.seed
python -c "from app.database import check_database_connection; print(check_database_connection())"
```

For macOS/Linux, activate with `source .venv/bin/activate`. `python -m app.seed` replaces only the named demo merchant dataset and is safe to rerun. It does not delete Razorpay-source records. Do not use `alembic downgrade base` unless you intentionally want to remove development tables/data.

### 4. Run the backend

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Verify [health](http://localhost:8000/health) or open [FastAPI docs](http://localhost:8000/docs).

### 5. Run the frontend

In a second terminal from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Start the backend first because the Next.js pages load operational and evaluation data server-side.

## Reproduce the evaluation

From `backend` with its virtual environment active:

```powershell
# Benchmark A — seed 42
python -m app.evaluation.run --benchmark specification --json

# Benchmark B — seed 314159
python -m app.evaluation.run --benchmark robustness --json
```

Generated reports overwrite `backend/generated/evaluation/latest.json` and `robustness.json`. That directory is ignored. All serialized fields except runtime/throughput reproduce exactly for the same code and seed. Expect A to report no mismatches and B to report the two known split-capture `UNRESOLVED` cases. Timing is machine-dependent and measures only local in-memory generation, hashing, reconciliation, metrics, and report assembly—not API or payment-processing capacity.

## Verification commands

```powershell
# Backend
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app
.\.venv\Scripts\python.exe -m app.evaluation.run --benchmark specification
.\.venv\Scripts\python.exe -m app.evaluation.run --benchmark robustness

# Frontend (from ../frontend)
npm run typecheck
npm run lint
npm run build
```

## Five-minute demo path

1. State the payment-operations problem and deterministic-vs-AI design.
2. Show source-aware dashboard metrics and payment records.
3. Complete or show the normalized INR 100 Razorpay Test Mode payment.
4. Ask Copilot why recent Razorpay payments failed and inspect its evidence chips.
5. Ask about the demo settlement shortfall and show recorded arithmetic.
6. Open Evaluation and contrast Benchmark A with the adversarial Benchmark B.
7. Filter mismatches and expand a split-capture safe failure.
8. Close on architecture, read-only boundaries, and honest limitations.

## Repository structure

```text
backend/
  app/api/                 # Operational, webhook, Copilot, evaluation APIs
  app/ai/                  # Prompt, strict tool schemas, dispatcher, agent loop
  app/evaluation/          # Generators, deterministic engine, metrics, CLI
  app/integrations/        # Razorpay Test Mode client, mapper, sync, webhooks
  alembic/                 # PostgreSQL migrations
  tests/                   # Backend regression and integrity tests
frontend/
  app/                     # Next.js routes, including /copilot and /evaluation
  components/              # Dashboard, Copilot, and audit UI
docs/                      # Architecture and detailed evaluation methodology
database/                  # Database notes
docker-compose.yml         # Local PostgreSQL 16 service
```

## Known limitations

- Benchmarks are developer-authored synthetic evaluations, not independent production validation.
- Split-capture aggregation and general multi-payment settlement allocation are unsupported.
- Operational evidence adapters are narrower than a full production finance system.
- Benchmark throughput is local in-memory reconciliation speed, not payment-processing capacity.
- Benchmark cases are isolated and unavailable to operational Copilot tools.
- AI access is read-only; there are no capture, refund, settlement, transfer, or resolution actions.
- There is no production-scale multi-tenant deployment, authentication layer, or Live Mode account linking claim.
- FX, chargebacks, broad tax inference, and production observability are outside the current scope.

## Screenshots

No repository screenshots are currently included. Add reviewed dashboard, Copilot, and Evaluation screenshots under a future `docs/assets/` directory before submission if the platform benefits from static previews. Do not use screenshots containing credentials, personal data, tunnel URLs, or hidden operational details.

## Submission checklist

- [x] Submission-grade README and architecture documentation
- [x] Reproducible Specification and Robustness benchmark commands
- [x] Known limitations and synthetic-data disclaimer
- [x] Automated backend/frontend verification
- [ ] Confirm public repository visibility and final repository URL
- [ ] Add a license after choosing terms
- [ ] Add reviewed screenshots if useful
- [ ] Record and review the five-minute demo video
- [ ] Complete Buildathon submission form/details

## Security posture

Secrets are loaded from ignored environment files. Webhook signatures are verified against the raw body, event IDs are unique, AI tools are read-only and source-scoped, the model has no direct database access, and benchmark execution is isolated from operational records. These are implementation controls—not a claim of PCI compliance, bank-grade security, or production security certification.

## License

No license is currently included. Reviewers receive no implied reuse rights; the repository owner should choose and add appropriate terms before public release.
