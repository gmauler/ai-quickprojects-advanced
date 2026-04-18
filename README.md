# ai-quickprojects-advanced

A collection of advanced AI engineering projects — Round 2 of a hands-on learning plan.
Each project is a production-grade component built with real tools used in industry.

## What this is

After completing [ai-quickprojects](https://github.com/gmauler/ai-quickprojects) (20 daily beginner projects),
this repository steps up the complexity — databases, async queues, React dashboards,
Docker, and multi-agent systems. Every project is designed to be a building block
of a real AI-powered SaaS product.

## Projects

| # | Project | Description | Stack | Status |
|---|---------|-------------|-------|--------|
| 01 | [Persistent Memory Chat](./projeto-01-memoria) | Chatbot that remembers conversations across sessions | PostgreSQL, psycopg2 | ✅ |
| 02 | [Intelligent API Cache](./projeto-02-cache) | Redis cache that avoids redundant API calls | Redis, FastAPI | ✅ |
| 03 | [Analytics Dashboard](./projeto-03-dashboard) | Real-time React dashboard for API metrics | React, Recharts, PostgreSQL | ✅ |
| 04 | [Async Task Queue](./projeto04celery) | Background processing with Celery and Flower | Celery, Redis, FastAPI | ✅ |
| 05 | Vector Store with pgvector | Semantic search over documents using embeddings | pgvector, PostgreSQL | ⏳ |
| 06 | Episodic Memory Agent | Agent that learns and updates user knowledge | PostgreSQL, embeddings | ⏳ |
| 07 | Multi-Agent Orchestrator | Delegates tasks to specialised sub-agents | FastAPI, asyncio | ⏳ |
| 08 | Code Execution Agent | Writes and runs Python in an isolated sandbox | Docker, FastAPI | ⏳ |
| 09 | Document Pipeline | Async PDF processing with semantic indexing | PyMuPDF, pgvector, Celery | ⏳ |
| 10 | Monitoring Agent | Watches URLs for changes and sends smart alerts | APScheduler, SMTP | ⏳ |
| 11 | Streaming Chat UI | React chat with real-time token streaming | React, FastAPI SSE | ⏳ |
| 12 | Document Search Dashboard | Drag-and-drop PDF upload with semantic search | React, pgvector | ⏳ |
| 13 | Prompt A/B Testing Tool | Side-by-side prompt comparison with metrics | React, Monaco Editor | ⏳ |
| 14 | Voice Assistant | Record audio, transcribe with Whisper, reply with Claude | Whisper, Web Audio API | ⏳ |
| 15 | Automated PDF Reports | Upload data, analyse with Claude, generate PDF | ReportLab, React | ⏳ |
| 16 | Dockerised Stack | Full stack containerised with docker-compose | Docker, nginx | ⏳ |
| 17 | Full CI/CD Pipeline | Tests → Docker build → push → auto deploy | GitHub Actions, Docker Hub | ⏳ |
| 18 | Structured Logging | Request correlation, Sentry integration, error dashboard | structlog, Sentry | ⏳ |
| 19 | JWT Auth + Rate Limiting | Production-ready API with auth and per-user quotas | JWT, Redis, bcrypt | ⏳ |
| 20 | Full AI SaaS | Everything combined into one deployable product | Full stack | ⏳ |

## Infrastructure

All projects share the same local infrastructure:

```bash
# PostgreSQL
docker run --name postgres-ai \
  -e POSTGRES_PASSWORD=password123 \
  -e POSTGRES_DB=aidb \
  -p 5432:5432 -d postgres:16

# Redis
docker run --name redis-ai -p 6379:6379 -d redis:7
```

## Environment

```bash
# Required for all projects
export ANTHROPIC_API_KEY=sk-ant-...
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop
- Git

## About

Built by **Gustavo Mauler**

Part of a personal learning plan to go from AI basics to production-grade
AI engineering. Each project solves a real problem and uses tools
that professional teams rely on daily.

→ See the beginner round: [ai-quickprojects](https://github.com/gmauler/ai-quickprojects)