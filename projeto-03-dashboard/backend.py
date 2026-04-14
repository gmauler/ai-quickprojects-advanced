import anthropic
import os
import psycopg2
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
app = FastAPI()

# CORS para o React conseguir chamar o backend
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

def conectar():
    return psycopg2.connect(**DB_CONFIG)

def criar_tabelas():
    conn = conectar()
    cur = conn.cursor()
    # Tabela que guarda cada chamada à API com métricas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_logs (
            id SERIAL PRIMARY KEY,
            modelo VARCHAR(50),
            tokens_input INTEGER,
            tokens_output INTEGER,
            latencia_ms INTEGER,
            custo_usd NUMERIC(10, 6),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def calcular_custo(modelo: str, tokens_in: int, tokens_out: int) -> float:
    # Preços aproximados do claude-haiku por 1M tokens
    preco_input = 0.25 / 1_000_000
    preco_output = 1.25 / 1_000_000
    return (tokens_in * preco_input) + (tokens_out * preco_output)

def guardar_log(modelo, tokens_in, tokens_out, latencia_ms, custo):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO api_logs (modelo, tokens_input, tokens_output, latencia_ms, custo_usd)
        VALUES (%s, %s, %s, %s, %s)
    """, (modelo, tokens_in, tokens_out, latencia_ms, custo))
    conn.commit()
    cur.close()
    conn.close()

class Pedido(BaseModel):
    prompt: str

@app.on_event("startup")
def startup():
    criar_tabelas()

@app.post("/chat")
def chat(pedido: Pedido):
    modelo = "claude-haiku-4-5-20251001"
    inicio = time.time()

    response = client.messages.create(
        model=modelo,
        max_tokens=1024,
        messages=[{"role": "user", "content": pedido.prompt}]
    )

    latencia_ms = int((time.time() - inicio) * 1000)
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    custo = calcular_custo(modelo, tokens_in, tokens_out)

    # Guarda métricas na base de dados
    guardar_log(modelo, tokens_in, tokens_out, latencia_ms, custo)

    return {
        "resposta": response.content[0].text,
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "latencia_ms": latencia_ms,
        "custo_usd": round(custo, 6)
    }

@app.get("/analytics/resumo")
def resumo():
    # Métricas totais agregadas
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COUNT(*) as total_chamadas,
            SUM(tokens_input + tokens_output) as total_tokens,
            ROUND(AVG(latencia_ms)) as latencia_media,
            ROUND(SUM(custo_usd)::numeric, 6) as custo_total
        FROM api_logs
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return {
        "total_chamadas": row[0],
        "total_tokens": row[1] or 0,
        "latencia_media_ms": row[2] or 0,
        "custo_total_usd": float(row[3] or 0)
    }

@app.get("/analytics/historico")
def historico():
    # Últimas 20 chamadas para o gráfico de linha
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            id,
            latencia_ms,
            tokens_input + tokens_output as tokens_total,
            custo_usd,
            TO_CHAR(created_at, 'HH24:MI:SS') as hora
        FROM api_logs
        ORDER BY created_at DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {"id": r[0], "latencia": r[1], "tokens": r[2], 
         "custo": float(r[3]), "hora": r[4]}
        for r in reversed(rows)
    ]