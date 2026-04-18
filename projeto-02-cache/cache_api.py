import anthropic
import os
import redis
import hashlib
import json
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Redis connection — used as both cache store and TTL manager
cache = redis.Redis(host="localhost", port=6379, decode_responses=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache TTL in seconds (1 hour)
CACHE_TTL = 3600

def make_hash(text: str) -> str:
    """Generate a deterministic MD5 hash for a given prompt."""
    return hashlib.md5(text.encode()).hexdigest()

def call_claude(prompt: str) -> tuple[str, float]:
    """Call the Claude API and return the response text and latency."""
    start = time.time()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    latency = time.time() - start
    return response.content[0].text, latency

class Request(BaseModel):
    prompt: str

@app.post("/chat")
def chat(request: Request):
    """
    Process a prompt with intelligent caching.
    Returns cached response if available, otherwise calls Claude API.
    """
    cache_key = f"cache:{make_hash(request.prompt)}"

    # Check cache before calling the API
    cached = cache.get(cache_key)
    if cached:
        data = json.loads(cached)
        return {
            "response": data["response"],
            "cache": "HIT",
            "latency_ms": 0,
            "tokens_saved": data["tokens"]
        }

    # Cache miss — call the API and store the result
    response, latency = call_claude(request.prompt)

    data = {"response": response, "tokens": len(request.prompt.split())}
    cache.setex(cache_key, CACHE_TTL, json.dumps(data))

    return {
        "response": response,
        "cache": "MISS",
        "latency_ms": round(latency * 1000),
        "tokens_saved": 0
    }

@app.get("/stats")
def stats():
    """Return Redis cache statistics."""
    info = cache.info()
    keys = cache.keys("cache:*")
    return {
        "cached_entries": len(keys),
        "hits": info.get("keyspace_hits", 0),
        "misses": info.get("keyspace_misses", 0),
        "memory_used": info.get("used_memory_human", "N/A")
    }

@app.delete("/cache")
def clear_cache():
    """Delete all cached entries."""
    keys = cache.keys("cache:*")
    if keys:
        cache.delete(*keys)
    return {"deleted": len(keys)}