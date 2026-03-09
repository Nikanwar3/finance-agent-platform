# Apex Capital Partners - AI Agentic Finance Operations
Automated month-end close using an orchestrator running 10 autonomous financial agents through Agno framework.

## Architecture
- **Multi-Agent Engine**: Agno (Python) backing 10 AI Agents.
- **Backend API**: FastAPI (Python) tracking states via PostgreSQL + Redis.
- **Frontend Dashboard**: Next.js + TailwindCSS with WebSocket live activity feed.

## Setup Instructions (< 15 Minutes)

### Prerequisites Check
- Docker & Docker Compose
- `OPENAI_API_KEY` (or equivalent Anthropic/Gemini)

### Step 1: Clone & Configure
```bash
git clone <repository>
cd finance_agent_platform

# Create environment configuration
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

### Step 2: Launch via Docker
Spin up the entire stack seamlessly. This launches Frontend, Backend API, Redis, and Postgres:
```bash
docker-compose up -d --build
```
> The underlying Postgres database will be instantly seeded with month-end financial datasets from 8 portfolio companies upon backend initialization. 

### Step 3: View Dashboard
Head to [http://localhost:3000](http://localhost:3000)
- Watch the 8 portfolios load.
- Click **"Run All Portfolios"** to initiate the AI orchestrated close pipeline autonomously.
- Real-time event streams will update the exact reasoning of individual sub-agents identifying anomalies or reconciling balance sheets.

## What is Happening Systemically?
1. **OrchestratorAgent** receives the run trigger.
2. It parallelly drops tasks into the Celery task queue, consumed by `TrialBalanceValidator`, `VarianceAnalysisAgent`, and `CashFlowReconciliationAgent`.
3. Agent outputs are written to the Shared Redis buffer and mapped to state endpoints via FastAPI.
4. Next.js picks it up over the continuous WebSocket pipeline, painting the progress dashboard flawlessly in real-time.
