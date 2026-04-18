# Project 04 — Async Task Queue with Celery

A production-grade async processing system using Celery and Redis.
Heavy Claude API calls are offloaded to background workers —
the API returns a job_id instantly while processing happens in the background.

## What I learned
- Why synchronous APIs block and how async queues solve it
- Setting up Celery with Redis as broker and result backend
- Tracking task progress with custom states (STARTED, PROGRESS, SUCCESS)
- Monitoring workers and tasks with the Flower dashboard
- The difference between broker and backend in a task queue

## How it works
POST /process
↓ returns job_id immediately
Celery Worker picks up task from Redis queue
↓ processes with Claude API
↓ stores result in Redis backend
GET /status/{job_id}
↓ returns current progress and result

## Prerequisites

- Docker running Redis:
```bash
  docker run --name redis-ai -p 6379:6379 -d redis:7
```
- `ANTHROPIC_API_KEY` environment variable set

## Setup

Start three processes in separate terminals:

```bash
# Terminal 1 — Celery worker
celery -A projeto04celery.tasks:app worker --loglevel=info --pool=solo

# Terminal 2 — Flower monitoring dashboard
celery -A projeto04celery.tasks:app flower --port=5555

# Terminal 3 — FastAPI server
uvicorn projeto04celery.api:app --reload --port=8001
```

Open **http://localhost:5555** to monitor tasks in real time.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/process` | Submit a document for async processing |
| POST | `/process-multiple` | Submit multiple documents |
| GET | `/status/{job_id}` | Poll task progress and result |
| GET | `/jobs` | Link to Flower dashboard |

## Stack

`Python` · `Celery` · `Redis` · `FastAPI` · `Flower` · `Anthropic API`