import anthropic
import os
import psycopg2
import json
import uuid
import time
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import tempfile

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

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
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS docs (
            id VARCHAR(36) PRIMARY KEY,
            filename VARCHAR(255),
            content TEXT,
            summary TEXT,
            status VARCHAR(20) DEFAULT 'processing',
            chunk_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doc_chunks (
            id SERIAL PRIMARY KEY,
            doc_id VARCHAR(36) REFERENCES docs(id),
            chunk_index INTEGER,
            content TEXT,
            embedding vector(384)
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding
        ON doc_chunks USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 10)
    """)
    conn.commit()
    cur.close()
    conn.close()

create_tables()

def chunk_text(text: str, size: int = 400, overlap: int = 80) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        chunks.append(" ".join(words[start:start + size]))
        start += size - overlap
    return chunks

def extract_text(path: str, suffix: str) -> str:
    if suffix == ".pdf":
        import fitz
        doc = fitz.open(path)
        return " ".join(page.get_text() for page in doc).strip()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """
    Accept a file upload, save temporarily, run the full pipeline,
    and return the document ID for status polling.
    """
    doc_id = str(uuid.uuid4())
    suffix = Path(file.filename).suffix.lower()

    if suffix not in [".pdf", ".txt", ".md"]:
        raise HTTPException(400, "Unsupported file type. Use PDF, TXT or MD.")

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # Insert document record with processing status
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO docs (id, filename, status) VALUES (%s, %s, 'processing')",
        (doc_id, file.filename)
    )
    conn.commit()
    cur.close()
    conn.close()

    # Process synchronously for simplicity
    # In production this would be a Celery task (Project 04)
    try:
        text = extract_text(tmp_path, suffix)
        chunks = chunk_text(text)
        embeddings = embedding_model.encode(chunks)

        # Generate summary
        truncated = " ".join(text.split()[:2000])
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": f"Summarise this document in 3 bullet points:\n\n{truncated}"}]
        )
        summary = response.content[0].text

        # Store chunks with embeddings
        conn = connect()
        cur = conn.cursor()
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            cur.execute(
                "INSERT INTO doc_chunks (doc_id, chunk_index, content, embedding) VALUES (%s, %s, %s, %s)",
                (doc_id, i, chunk, json.dumps(emb.tolist()))
            )
        cur.execute("""
            UPDATE docs SET status='ready', content=%s, summary=%s, chunk_count=%s
            WHERE id=%s
        """, (text[:5000], summary, len(chunks), doc_id))
        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        conn = connect()
        cur = conn.cursor()
        cur.execute("UPDATE docs SET status='error' WHERE id=%s", (doc_id,))
        conn.commit()
        cur.close()
        conn.close()

    finally:
        os.unlink(tmp_path)

    return {"doc_id": doc_id, "filename": file.filename}

@app.get("/documents")
def list_documents():
    """Return all documents with their status and metadata."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, filename, status, summary, chunk_count, created_at
        FROM docs ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{
        "id": r[0], "filename": r[1], "status": r[2],
        "summary": r[3], "chunks": r[4],
        "created_at": r[5].isoformat() if r[5] else None
    } for r in rows]

@app.get("/documents/{doc_id}")
def get_document(doc_id: str):
    """Return a single document with full details."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, filename, status, summary, chunk_count FROM docs WHERE id=%s", (doc_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(404, "Document not found")
    return {"id": row[0], "filename": row[1], "status": row[2], "summary": row[3], "chunks": row[4]}

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

@app.post("/search")
def search(request: SearchRequest):
    """
    Semantic search across all indexed document chunks.
    Returns matching chunks with similarity scores and source document info.
    """
    query_embedding = embedding_model.encode(request.query).tolist()

    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.filename, d.id, c.content, c.chunk_index,
               1 - (c.embedding <=> %s::vector) as similarity
        FROM doc_chunks c
        JOIN docs d ON c.doc_id = d.id
        WHERE d.status = 'ready'
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """, (json.dumps(query_embedding), json.dumps(query_embedding), request.limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [{
        "filename": r[0],
        "doc_id": r[1],
        "content": r[2],
        "chunk_index": r[3],
        "similarity": round(float(r[4]), 4)
    } for r in rows]

@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    """Delete a document and all its chunks."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM doc_chunks WHERE doc_id=%s", (doc_id,))
    cur.execute("DELETE FROM docs WHERE id=%s", (doc_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"deleted": doc_id}