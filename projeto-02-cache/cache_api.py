import anthropic
import os
import redis
import hashlib
import json
import time
from fastapi import FastAPI
from pydantic import BaseModel

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
cache = redis.Redis(host="localhost", port=6379, decode_responses=True)
app = FastAPI()

CACHE_TTL = 3600

def fazer_hash(texto: str) -> str:
    return hashlib.md5(texto.encode()).hexdigest()

def chamar_claude(prompt: str) -> tuple[str, float]:
    inicio = time.time()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    latencia = time.time() - inicio
    return response.content[0].text, latencia

class Pedido(BaseModel):
    prompt: str

@app.post("/chat")
def chat(pedido: Pedido):
    chave = f"cache:{fazer_hash(pedido.prompt)}"

    cached = cache.get(chave)
    if cached:
        dados = json.loads(cached)
        return {
            "resposta": dados["resposta"],
            "cache": "HIT",
            "latencia_ms": 0,
            "tokens_poupados": dados["tokens"]
        }

    resposta, latencia = chamar_claude(pedido.prompt)

    dados = {"resposta": resposta, "tokens": len(pedido.prompt.split())}
    cache.setex(chave, CACHE_TTL, json.dumps(dados))

    return {
        "resposta": resposta,
        "cache": "MISS",
        "latencia_ms": round(latencia * 1000),
        "tokens_poupados": 0
    }

@app.get("/stats")
def stats():
    info = cache.info()
    keys = cache.keys("cache:*")
    return {
        "entradas_em_cache": len(keys),
        "hits": info.get("keyspace_hits", 0),
        "misses": info.get("keyspace_misses", 0),
        "memoria_usada": info.get("used_memory_human", "N/A")
    }

@app.delete("/cache")
def limpar_cache():
    keys = cache.keys("cache:*")
    if keys:
        cache.delete(*keys)
    return {"eliminadas": len(keys)}