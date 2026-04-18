# Project 03 — Real-time Analytics Dashboard

A React dashboard that tracks every Claude API call in real-time —
latency, token usage, and estimated cost — stored in PostgreSQL and
visualised with live-updating charts.

## What I learned
- Building React components with useState and useEffect hooks
- Fetching data from a FastAPI backend with axios
- Rendering live charts with Recharts
- Tracking API usage metrics (tokens, latency, cost) in PostgreSQL
- The difference between input and output tokens in LLM pricing

## How it works
React Dashboard (port 5173)
↓ axios GET every 5s
FastAPI Backend (port 8000)
↓ INSERT on every /chat call
PostgreSQL
↑ SELECT aggregates for /analytics/summary
↑ SELECT last 20 rows for /analytics/history

## Prerequisites

- Docker running PostgreSQL and Redis
- `ANTHROPIC_API_KEY` environment variable set
- Node.js 18+

## Setup

```bash
# Backend
pip install anthropic fastapi uvicorn psycopg2-binary
uvicorn projeto-03-dashboard.backend:app --reload

# Frontend
cd projeto-03-dashboard/frontend
npm install
npm run dev
```

Open **http://localhost:5173**

## Stack

`Python` · `FastAPI` · `PostgreSQL` · `React` · `Recharts` · `Anthropic API`