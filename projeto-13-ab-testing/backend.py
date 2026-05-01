import anthropic
import os
import psycopg2
import json
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_CONFIG = {
    "host": "localhost", "port": 5432,
    "database": "aidb", "user": "postgres", "password": "password123"
}

def connect():
    return psycopg2.connect(**DB_CONFIG)

def create_tables():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ab_experiments (
            id SERIAL PRIMARY KEY,
            input_text TEXT,
            prompt_a TEXT,
            prompt_b TEXT,
            response_a TEXT,
            response_b TEXT,
            tokens_a INTEGER,
            tokens_b INTEGER,
            latency_a_ms INTEGER,
            latency_b_ms INTEGER,
            cost_a NUMERIC(10,6),
            cost_b NUMERIC(10,6),
            winner VARCHAR(1),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

create_tables()

def call_claude(system_prompt: str, user_input: str) -> dict:
    """Call Claude and return response with metrics."""
    start = time.time()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_input}]
    )
    latency_ms = int((time.time() - start) * 1000)
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    cost = (tokens_in * 0.25 + tokens_out * 1.25) / 1_000_000

    return {
        "text": response.content[0].text,
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "total_tokens": tokens_in + tokens_out,
        "latency_ms": latency_ms,
        "cost_usd": round(cost, 6)
    }

class RunRequest(BaseModel):
    input_text: str
    prompt_a: str
    prompt_b: str

class SaveRequest(BaseModel):
    input_text: str
    prompt_a: str
    prompt_b: str
    response_a: dict
    response_b: dict
    winner: str

@app.post("/run")
async def run_experiment(request: RunRequest):
    """
    Run both prompts against the same input simultaneously.
    Uses sequential calls (parallel would require async client).
    """
    result_a = call_claude(request.prompt_a, request.input_text)
    result_b = call_claude(request.prompt_b, request.input_text)

    return {
        "a": result_a,
        "b": result_b
    }

@app.post("/save")
def save_result(request: SaveRequest):
    """Save experiment result with winner to database."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ab_experiments
        (input_text, prompt_a, prompt_b, response_a, response_b,
         tokens_a, tokens_b, latency_a_ms, latency_b_ms,
         cost_a, cost_b, winner)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        request.input_text,
        request.prompt_a, request.prompt_b,
        request.response_a["text"], request.response_b["text"],
        request.response_a["total_tokens"], request.response_b["total_tokens"],
        request.response_a["latency_ms"], request.response_b["latency_ms"],
        request.response_a["cost_usd"], request.response_b["cost_usd"],
        request.winner
    ))
    conn.commit()
    cur.close()
    conn.close()
    return {"saved": True}

@app.get("/history")
def get_history():
    """Return all saved experiments ordered by most recent."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, input_text, winner, tokens_a, tokens_b,
               latency_a_ms, latency_b_ms, cost_a, cost_b, created_at
        FROM ab_experiments
        ORDER BY created_at DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{
        "id": r[0],
        "input": r[1][:80] + "..." if len(r[1]) > 80 else r[1],
        "winner": r[2],
        "tokens_a": r[3], "tokens_b": r[4],
        "latency_a": r[5], "latency_b": r[6],
        "cost_a": float(r[7]), "cost_b": float(r[8]),
        "created_at": r[9].isoformat()
    } for r in rows]