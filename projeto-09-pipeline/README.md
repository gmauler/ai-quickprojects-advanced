# Project 09 — Document Processing Pipeline

An automated pipeline that ingests documents (PDF, TXT, MD),
extracts text, generates semantic embeddings, summarises content,
and extracts entities — making everything searchable by meaning.

## What I learned
- Building multi-stage document processing pipelines
- Text chunking with overlap to preserve context at boundaries
- Batch embedding generation for efficiency
- Entity extraction from unstructured text using Claude
- Combining pgvector semantic search with structured metadata

## How it works
Document (PDF / TXT / MD)
↓ [Stage 1] Extract raw text
↓ [Stage 2] Split into overlapping chunks (500 words, 100 overlap)
↓ [Stage 3] Generate embeddings → store in pgvector
↓ [Stage 4] Generate executive summary (Claude)
↓ [Stage 5] Extract entities: dates, components, actions
↓
Fully indexed — ready for semantic search

## Real-world application
This pipeline is the foundation for automatic TSG generation from:
- Resolved incident reports
- Engineer investigation notes (Copilot CLI sessions)
- Existing runbooks and documentation
- Historical KQL query libraries

## Prerequisites
- Docker running PostgreSQL with pgvector
- `ANTHROPIC_API_KEY` environment variable set

## Setup

```bash
pip install anthropic pymupdf sentence-transformers psycopg2-binary
python pipeline.py
```

## Stack

`Python` · `PostgreSQL` · `pgvector` · `sentence-transformers` · `PyMuPDF` · `Anthropic API`