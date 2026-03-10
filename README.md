# 🤖 Apex Capital Partners - Agentic Finance Operations Platform

![Next.js](https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js)
![React](https://img.shields.io/badge/React-19-blue?style=for-the-badge&logo=react)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-4-38B2AC?style=for-the-badge&logo=tailwind-css)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-316192?style=for-the-badge&logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker)

A production-grade, autonomous agentic AI system for private equity finance operations. This platform automates the month-end close process across 8 portfolio companies using a multi-agent orchestration pattern powered by the **Agno Framework** and **OpenAI/Claude**.

---

## 🌟 Key Features

- **Multi-Agent Orchestration**: 10 specialized financial AI agents coordinated by a central Orchestrator Agent.
- **Autonomous Operations**: Agents work concurrently and sequentially to perform trial balance validation, variance analysis, accrual verification, and more without manual intervention.
- **Real-Time Dashboard**: A polished Next.js user interface featuring live WebSockets streams of agent activities and dynamic progress tracking.
- **Financial Validation**: Embedded accounting logic for ASC 606 revenue recognition, intercompany eliminations, and GAP consolidations.
- **Simulated Financial Data**: Seamlessly seeds a mock, realistic accounting dataset for 8 unique portfolio companies to validate agent reasoning.

---

## 🏗️ System Architecture

### Multi-Agent Grouping Pattern
The `OrchestratorAgent` manages state transitions and handoffs using Redis for shared memory across 4 distinct execution groups:

1. **Parallel Execution Group 1**: `TrialBalanceValidator`, `VarianceAnalysisAgent`, `CashFlowReconciliationAgent`
2. **Sequential Execution Group 2**: `AccrualVerificationAgent`, `RevenueRecognitionAgent`, `ExpenseCategorizationAgent`
3. **Cross-Company Group 3**: `IntercompanyEliminationAgent`
4. **Final Consolidation Group 4**: `ConsolidationAgent`, `ReportingCommunicationAgent`

### Tech Stack
- **Frontend**: Next.js 15 (App Router), React, Tailwind CSS 4, Recharts, Lucide Icons, Socket.io-client.
- **Backend API**: Python, FastAPI, SQLAlchemy (ORM).
- **Agent Framework**: Agno Framework executing OpenAI `gpt-4o-mini` reasoning.
- **Infrastructure**: PostgreSQL (Primary State), Redis (Agent memory/PubSub), Docker & Docker Compose.

---

## 🚀 Quick Setup Instructions (< 5 Minutes)

### Prerequisites
- [Docker & Docker Compose](https://docs.docker.com/get-docker/) installed.
- An API Key from OpenAI (or Anthropic/Gemini)

### Step 1: Clone the Repository
```bash
git clone https://github.com/Nikanwar3/finance-agent-platform.git
cd finance-agent-platform
```

### Step 2: Configure Environment
Copy the example environment variables and add your AI provider API key.
```bash
cp .env.example .env
```
Open `.env` and configure:
```env
OPENAI_API_KEY=your_api_key_here
DATABASE_URL=postgresql://admin:password@postgres:5432/finance_db
REDIS_URL=redis://redis:6379/0
```

### Step 3: Launch with Docker
The entire stack (Frontend, Backend, Database, Cache) is securely containerized.
```bash
docker-compose up -d --build
```
> **Note**: During backend initialization, the PostgreSQL database is automatically populated with robust sample financial datasets spanning 3 months across 8 mock portfolio companies.

### Step 4: Access the Platform
- **Dashboard**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🎥 Video Demonstration

<!-- Replace the link below with your actual Loom or YouTube unlisted link -->
[**Watch the 5-Minute Platform Walkthrough Here**](https://example.com/demo-link-placeholder)

The video covers:
1. Autonomous multi-agent operations (no manual clicking between states).
2. Live WebSocket updates streaming agent reasoning to the frontend.
3. Full view of the generated month-end close lifecycle.

---

## 📂 Repository Structure

```text
 finance-agent-platform/
 ├── backend/
 │   ├── app/
 │   │   ├── agents/          # Agno agent configurations & workflows
 │   │   ├── api/             # FastAPI REST routes & WebSockets
 │   │   ├── core/            # App configurations
 │   │   ├── models/          # SQLAlchemy Database Models
 │   │   └── schemas/         # Pydantic validation schemas
 │   ├── data/                # Generated financial CSV datasets
 │   ├── generate_data.py     # Python script to generate mock PE data
 │   ├── main.py              # Application entrypoint
 │   ├── requirements.txt     # Python dependencies
 │   └── Dockerfile           # Backend container instructions
 ├── frontend/
 │   ├── src/app/             # Next.js Pages, Routing & Dashboard UI
 │   ├── public/              # Static assets
 │   ├── package.json         # Node.js dependencies
 │   └── Dockerfile           # Frontend container instructions
 ├── docker-compose.yml       # Full stack deployment configuration
 ├── .env.example             # Env secrets template
 └── README.md                # Project documentation
```

---

## 🧠 Design Philosophy & Trade-offs
- **WebSocket over Polling**: For high-fidelity agent updates, native WebSocket streams were prioritized to deliver instantaneous feedback to the user regarding agent decision-making.
- **Relational + In-Memory State**: PostgreSQL reliably stores the persistent entities (Company ARR, Close Progress, Metrics), whilst Redis handles transient agent communication, handoffs, and temporary workflow execution memories ensuring non-blocking operations.
- **Agent Execution**: Agno provided an incredibly robust framework structure. I utilized dependency injection alongside an orchestrator pattern to handle fail-safes and concurrent parallel executions for groups resolving simple tasks versus sequential execution for interrelated tasks (like accruals and rev-rec requiring settled ledgers).

---

Developed for the Agentic AI Developer Assessment by Nidhi Kanwar.
