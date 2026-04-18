import anthropic
import os
import psycopg2
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": "localhost", "port": 5432,
    "database": "aidb", "user": "postgres", "password": "password123"
}

def connect():
    return psycopg2.connect(**DB_CONFIG)

def create_tables():
    """Create the api_logs table to track every API call with metrics."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_logs (
            id SERIAL PRIMARY KEY,
            model VARCHAR(50),
            tokens_input INTEGER,
            tokens_output INTEGER,
            latency_ms INTEGER,
            cost_usd NUMERIC(10, 6),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """
    Estimate cost in USD based on Anthropic's pricing.
    Haiku: $0.25 per 1M input tokens, $1.25 per 1M output tokens.
    """
    price_input = 0.25 / 1_000_000
    price_output = 1.25 / 1_000_000
    return (tokens_in * price_input) + (tokens_out * price_output)

def save_log(model, tokens_in, tokens_out, latency_ms, cost):
    """Persist API call metrics to the database."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO api_logs (model, tokens_input, tokens_output, latency_ms, cost_usd)
        VALUES (%s, %s, %s, %s, %s)
    """, (model, tokens_in, tokens_out, latency_ms, cost))
    conn.commit()
    cur.close()
    conn.close()

class Request(BaseModel):
    prompt: str

@app.on_event("startup")
def startup():
    create_tables()

@app.post("/chat")
def chat(request: Request):
    """Call Claude API and log metrics for every request."""
    model = "claude-haiku-4-5-20251001"
    start = time.time()

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": request.prompt}]
    )

    latency_ms = int((time.time() - start) * 1000)
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    cost = calculate_cost(model, tokens_in, tokens_out)

    save_log(model, tokens_in, tokens_out, latency_ms, cost)

    return {
        "response": response.content[0].text,
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "latency_ms": latency_ms,
        "cost_usd": round(cost, 6)
    }

@app.get("/analytics/summary")
def summary():
    """Return aggregated metrics across all API calls."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COUNT(*) as total_calls,
            SUM(tokens_input + tokens_output) as total_tokens,
            ROUND(AVG(latency_ms)) as avg_latency,
            ROUND(SUM(cost_usd)::numeric, 6) as total_cost
        FROM api_logs
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return {
        "total_calls": row[0],
        "total_tokens": row[1] or 0,
        "avg_latency_ms": row[2] or 0,
        "total_cost_usd": float(row[3] or 0)
    }

@app.get("/analytics/history")
def history():
    """Return the last 20 API calls for charting."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            id,
            latency_ms,
            tokens_input + tokens_output as total_tokens,
            cost_usd,
            TO_CHAR(created_at, 'HH24:MI:SS') as time
        FROM api_logs
        ORDER BY created_at DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {"id": r[0], "latency": r[1], "tokens": r[2],
         "cost": float(r[3]), "time": r[4]}
        for r in reversed(rows)
    ]