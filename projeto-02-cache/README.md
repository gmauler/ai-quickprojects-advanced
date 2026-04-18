# Project 02 — Intelligent API Cache with Redis

A FastAPI service that caches Claude API responses in Redis to avoid redundant
API calls. Identical prompts are served from cache with zero latency and zero cost.

## What I learned
- Using Redis as a key-value cache with TTL expiration
- Hashing prompts with MD5 to generate deterministic cache keys
- The difference between cache HIT and MISS patterns
- How caching reduces both latency and API costs in production

## How it works
Incoming prompt
↓
Hash prompt → check Redis
↓
HIT: return cached response (0ms, free)
MISS: call Claude API → store in Redis → return response

## Prerequisites

- Docker running Redis:
```bash
  docker run --name redis-ai -p 6379:6379 -d redis:7
```
- `ANTHROPIC_API_KEY` environment variable set

## Setup

```bash
pip install anthropic fastapi uvicorn redis
uvicorn projeto-02-cache.cache_api:app --reload
```

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Process prompt with caching |
| GET | `/stats` | View cache hit/miss statistics |
| DELETE | `/cache` | Clear all cached entries |

## Example

```bash
# First call — MISS (calls Claude API)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is machine learning?"}'

# Second call — HIT (served from Redis, 0ms)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is machine learning?"}'
```

## Stack

`Python` · `FastAPI` · `Redis` · `Anthropic API`