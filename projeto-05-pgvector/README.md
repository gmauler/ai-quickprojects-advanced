# Project 05 — Vector Store with pgvector

Semantic document search using real embeddings stored in PostgreSQL with the pgvector extension.
Unlike keyword search, semantic search understands meaning — "Redis" matches "fast in-memory cache"
even without exact word overlap.

## What I learned
- The difference between keyword search and semantic search
- What embeddings are and how they represent meaning as vectors
- Installing and using the pgvector PostgreSQL extension
- Cosine similarity as a distance metric between vectors
- Building a complete RAG pipeline with real embeddings

## How it works
Document text
↓ SentenceTransformer model
384-dimensional embedding vector
↓ INSERT INTO documents (embedding)
PostgreSQL + pgvector
↑ SELECT ... ORDER BY embedding <=> query_vector
Cosine similarity ranking
↓
Top K relevant chunks → Claude API → Answer

## Prerequisites

- Docker running PostgreSQL with pgvector:
```bash
  docker run --name postgres-ai \
    -e POSTGRES_PASSWORD=password123 \
    -e POSTGRES_DB=aidb \
    -p 5432:5432 -d pgvector/pgvector:pg16
```
- `ANTHROPIC_API_KEY` environment variable set

## Setup

```bash
pip install anthropic psycopg2-binary pgvector sentence-transformers
python vector_store.py
```

## Stack

`Python` · `PostgreSQL` · `pgvector` · `sentence-transformers` · `Anthropic API`