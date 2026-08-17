# ⚙️ Real-Time Financial Analysis Backend Platform

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-316192?style=for-the-badge&logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis)
![Celery](https://img.shields.io/badge/Celery-Background%20Workers-37814A?style=for-the-badge&logo=celery)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker)
![AWS](https://img.shields.io/badge/AWS-ECS%20%7C%20S3-FF9900?style=for-the-badge&logo=amazon-aws)
![pytest](https://img.shields.io/badge/pytest-24%20tests-0A9EDC?style=for-the-badge&logo=pytest)
![Next.js](https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js)

A backend platform for automating month-end financial close across a
portfolio of companies: concurrent workflow execution, a Postgres system of
record, Redis-backed background workers, real-time WebSocket progress
streaming, and the operational plumbing (rate limiting, structured logging,
centralized error handling, CI/CD to AWS) that a production API needs.

The financial-close logic itself is organized as a small set of concurrent,
dependency-ordered workers (validation → variance/accrual → intercompany
elimination) — an implementation detail of the orchestration engine, not the
headline. The headline is what actually had to be built to run that safely
at scale: a task queue instead of blocking the request thread, pub/sub
instead of polling, and the reliability layer around all of it.

---

## 🌟 What this demonstrates

- **Async request handling + background workers**: `POST /close/{id}`
  enqueues onto a Celery/Redis task queue and returns immediately; the
  actual multi-step workflow runs in a separate `worker` process, never on
  the request thread.
- **Real-time updates without polling**: the worker publishes progress
  events over Redis pub/sub; a relay thread in the API process forwards them
  to connected WebSocket clients.
- **Concurrent, dependency-ordered execution**: a small DAG scheduler
  (`DependencyGraph`, Kahn's algorithm) runs independent workflow steps in
  parallel and gates dependent ones until their inputs are settled —
  covered directly by unit tests (`tests/test_dependency_graph.py`).
- **Rate limiting**: per-route limits (Redis-backed, in-memory fallback for
  local dev) via `slowapi`, with 429s returned in the same structured error
  shape as every other error.
- **Structured logging**: every log line is a single JSON object tagged
  with a request ID that's threaded through the whole request lifecycle —
  queryable by field in CloudWatch/any log aggregator, not grepped as text.
- **Centralized error handling**: domain errors, validation errors, DB
  errors, and unhandled exceptions all normalize to one JSON envelope
  (`{"error": {"code", "message"}, "request_id"}`); internals are never
  leaked to the client.
- **API test suite**: 24 pytest tests covering endpoints, error handling,
  rate limiting, the DAG scheduler, and the AWS/S3 integration's
  graceful-degradation path — running against SQLite + an in-memory Redis
  fallback so CI needs no external services.
- **CI/CD**: GitHub Actions runs the backend test suite, frontend
  lint/build, and a Docker Compose build validation on every push; a
  separate tag-triggered workflow builds/pushes to ECR and deploys to ECS
  Fargate (see `deploy/aws/`).
- **AWS integration**: completed closes are archived as immutable JSON
  reports to S3 for audit trail purposes (`app/core/aws_client.py`) — with
  the same fallback-if-unavailable pattern used for Redis, so it never
  blocks local dev.

---

## 🏗️ Architecture

```
Client (Next.js)
   │  REST + WebSocket
   ▼
FastAPI (backend)
   │  request middleware: structured logging → rate limiting → error handling
   │
   ├─ PostgreSQL          — companies, issues, action logs (system of record)
   ├─ Redis               — Celery broker/backend, agent shared memory,
   │                         rate-limit counters, close-event pub/sub
   ├─ POST /close/{id}  → enqueues Celery task, returns immediately
   └─ WebSocket /ws     ← relayed close-event broadcasts (see below)

Celery worker (separate process/container)
   │  consumes the close-workflow task queue
   ├─ runs the dependency-ordered workflow steps (concurrent where safe)
   ├─ publishes progress events to Redis pub/sub  ──► relayed to WebSocket
   └─ archives the completed report to S3
```

### Tech Stack
- **Backend**: Python, FastAPI, SQLAlchemy (ORM), Celery (background workers).
- **Data/cache**: PostgreSQL (primary state), Redis (broker, shared memory,
  rate limiting, pub/sub).
- **Infra**: Docker & Docker Compose (local), AWS ECS Fargate + ECR + S3 +
  Secrets Manager (production — see `deploy/aws/README.md`).
- **CI/CD**: GitHub Actions (`.github/workflows/`).
- **Testing**: pytest, FastAPI `TestClient`.
- **Frontend**: Next.js 15 (App Router), React, Tailwind CSS, Recharts.

---

## 🚀 Quick Setup (Docker)

### Prerequisites
- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- An API key from OpenAI (or Anthropic/Gemini) for the workflow's reasoning steps

### Steps
```bash
git clone https://github.com/Nikanwar3/finance-agent-platform.git
cd finance-agent-platform
cp .env.example .env   # set OPENAI_API_KEY, optionally AWS_* for S3 archival
docker-compose up -d --build
```

This starts five services: `backend` (API), `worker` (Celery consumer),
`frontend`, `postgres`, `redis`. The backend seeds Postgres with three
months of sample financial data across 8 mock portfolio companies on first
boot.

- **Dashboard**: [http://localhost:3000](http://localhost:3000)
- **API docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health check**: [http://localhost:8000/health](http://localhost:8000/health)

## 🧪 Running tests locally (without Docker)

```bash
cd backend
pip install -r ../requirements.txt
pytest -v
```

Tests run against SQLite and an in-memory Redis/rate-limiter fallback, so no
external services are required — the same setup GitHub Actions uses in CI.

---

## 📂 Repository Structure

```text
finance-agent-platform/
├── backend/
│   ├── app/
│   │   ├── agents/          # Workflow step implementations + DAG scheduler
│   │   ├── api/             # FastAPI REST routes & WebSocket endpoint
│   │   ├── core/            # Config, logging, rate limiting, error handling,
│   │   │                     Celery app config, AWS/S3 client
│   │   ├── services/        # Redis pub/sub → WebSocket relay
│   │   ├── workers/         # Celery tasks (the actual close-workflow execution)
│   │   ├── models/          # SQLAlchemy models
│   │   └── schemas/         # Pydantic response schemas
│   ├── tests/                # pytest suite (API, errors, rate limits, DAG, AWS, logging)
│   ├── data/                  # Generated sample financial datasets
│   ├── generate_data.py
│   ├── requirements.txt      # (repo root)
│   └── Dockerfile             # Shared image for `backend` and `worker`
├── deploy/aws/                # ECS task definition + deployment architecture doc
├── .github/workflows/         # CI (test/lint/build) + CD (deploy to AWS)
├── frontend/                   # Next.js dashboard
└── docker-compose.yml          # backend, worker, frontend, postgres, redis
```

---

## 🧠 Design Notes

- **Task queue over `BackgroundTasks`**: FastAPI's built-in `BackgroundTasks`
  runs in the same process as the request — fine for an email, wrong for a
  multi-minute workflow. A Celery worker in its own process/container means
  the API stays responsive under load and the workflow can be retried,
  scaled, or monitored independently.
- **Pub/sub over polling**: the frontend previously polled every few
  seconds; progress events are now pushed to WebSocket clients the moment
  the worker publishes them, with polling kept only as a disconnect-safe
  fallback.
- **Graceful degradation, consistently applied**: Redis, the rate limiter,
  and S3 archival all fall back to a safe no-op/in-memory mode when their
  backing service isn't configured, rather than crashing local/CI runs that
  don't have every piece of infra wired up.
- **One error shape, everywhere**: whether a request 404s, 409s, 429s, or
  500s, the client parses the same `{"error": {"code", "message"}}`
  envelope — no branching on status code to figure out what happened.

---

Developed by Nidhi Kanwar.
