import anthropic
import os
import psycopg2
import json
from sentence_transformers import SentenceTransformer

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DB_CONFIG = {
    "host": "localhost", "port": 5432,
    "database": "aidb", "user": "postgres", "password": "password123"
}



def connect():
    return psycopg2.connect(**DB_CONFIG)

def create_tables():
    """
    Create the documents table with a vector column.
    The vector(1536) type stores embeddings from text-embedding-3-small.
    """
    conn = connect()
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            title VARCHAR(200),\
            content TEXT,
            -- vector(1536) stores the embedding as an array of 1536 floats
            embedding vector(384),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    # ivfflat index speeds up approximate nearest neighbour search
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_embedding 
        ON documents USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 10)
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Tables created with pgvector support!")

# Load model once at startup (downloads ~90MB on first run)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def get_embedding(text: str) -> list[float]:
    """
    Convert text to a 384-dimensional embedding vector using
    a local sentence transformer model. No API calls needed.
    """
    embedding = embedding_model.encode(text)
    return embedding.tolist()

def add_document(title: str, content: str):
    """Generate an embedding for the content and store it in the database."""
    print(f"  Generating embedding for: {title}")
    embedding = get_embedding(content)
    
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO documents (title, content, embedding) VALUES (%s, %s, %s)",
        (title, content, json.dumps(embedding))
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"  Stored: {title}")

def semantic_search(query: str, limit: int = 3, min_similarity: float = 0.3) -> list:
    """
    Find semantically similar documents above a minimum similarity threshold.
    Results below the threshold are filtered out to avoid irrelevant matches.
    """
    query_embedding = get_embedding(query)
    
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT title, content,
               1 - (embedding <=> %s::vector) as similarity
        FROM documents
        WHERE 1 - (embedding <=> %s::vector) > %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (
        json.dumps(query_embedding),
        json.dumps(query_embedding),
        min_similarity,
        json.dumps(query_embedding),
        limit
    ))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    return [
        {"title": r[0], "content": r[1][:200], "similarity": round(float(r[2]), 4)}
        for r in rows
    ]

def answer_with_context(question: str):
    relevant_docs = semantic_search(question, limit=3, min_similarity=0.3)
    
    if not relevant_docs:
        print(f"\nNo documents found above similarity threshold for: '{question}'")
        print("Try adding more relevant documents to the vector store.")
        return
    
    context = "\n\n---\n\n".join([
        f"[{doc['title']}] (similarity: {doc['similarity']})\n{doc['content']}"
        for doc in relevant_docs
    ])
    
    print(f"\nTop {len(relevant_docs)} relevant documents found:")
    for doc in relevant_docs:
        print(f"  {doc['similarity']:.4f} — {doc['title']}")
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""Answer the question using only the context below.
If the answer is not in the context, say so clearly.

Context:
{context}

Question: {question}"""
        }]
    )
    
    print(f"\nAnswer:\n{response.content[0].text}")
    """RAG pipeline: find relevant docs, then answer using Claude."""
    # Step 1: find relevant documents
    relevant_docs = semantic_search(question, limit=3)
    
    if not relevant_docs:
        print("No documents found.")
        return
    
    # Step 2: build context from search results
    context = "\n\n---\n\n".join([
        f"[{doc['title']}] (similarity: {doc['similarity']})\n{doc['content']}"
        for doc in relevant_docs
    ])
    
    print(f"\nTop {len(relevant_docs)} relevant documents found:")
    for doc in relevant_docs:
        print(f"  {doc['similarity']:.4f} — {doc['title']}")
    
    # Step 3: ask Claude with context
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""Answer the question using only the context below.
If the answer is not in the context, say so clearly.

Context:
{context}

Question: {question}"""
        }]
    )
    
    print(f"\nAnswer:\n{response.content[0].text}")

if __name__ == "__main__":
    create_tables()
    
    # Check if documents already exist to avoid duplicates
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM documents")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    if count == 0:
        print("\nAdding documents to vector store...")
        documents = [
            ("Python Basics", "Python is a high-level programming language known for its simplicity and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming."),
            ("Machine Learning", "Machine learning is a subset of artificial intelligence that enables systems to learn from data. Common algorithms include linear regression, decision trees, and neural networks."),
            ("PostgreSQL", "PostgreSQL is a powerful open-source relational database system. It supports advanced data types, full-text search, and extensions like pgvector for vector similarity search."),
            ("Docker Containers", "Docker is a platform for developing and running applications in containers. Containers package code and dependencies together, ensuring consistent environments across different machines."),
            ("REST APIs", "REST (Representational State Transfer) is an architectural style for building web services. APIs use HTTP methods like GET, POST, PUT, DELETE to perform operations on resources."),
            ("Neural Networks", "Neural networks are computing systems inspired by biological neural networks. They consist of layers of interconnected nodes that process information and learn patterns from training data."),
            ("Redis Cache", "Redis is an in-memory data store used as a cache, message broker, and queue. It supports data structures like strings, hashes, lists, and sorted sets with very low latency."),
            ("Async Programming", "Asynchronous programming allows programs to perform tasks concurrently without blocking. Python supports async/await syntax for writing non-blocking code with coroutines."),
        ]
        for title, content in documents:
            add_document(title, content)
        print(f"\nAdded {len(documents)} documents.")
    else:
        print(f"\n{count} documents already in store, skipping insertion.")
    
    print("\n" + "="*60)
    print("SEMANTIC SEARCH TESTS")
    print("="*60)
    
    answer_with_context("How do computers learn from examples?")
    print("\n" + "-"*60)
    answer_with_context("What is Redis used for?")
    print("\n" + "-"*60)
    answer_with_context("How does Docker help developers?")
    create_tables()
    
    # Add sample documents covering different topics
    print("\nAdding documents to vector store...")
    documents = [
        ("Python Basics", "Python is a high-level programming language known for its simplicity and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming."),
        ("Machine Learning", "Machine learning is a subset of artificial intelligence that enables systems to learn from data. Common algorithms include linear regression, decision trees, and neural networks."),
        ("PostgreSQL", "PostgreSQL is a powerful open-source relational database system. It supports advanced data types, full-text search, and extensions like pgvector for vector similarity search."),
        ("Docker Containers", "Docker is a platform for developing and running applications in containers. Containers package code and dependencies together, ensuring consistent environments across different machines."),
        ("REST APIs", "REST (Representational State Transfer) is an architectural style for building web services. APIs use HTTP methods like GET, POST, PUT, DELETE to perform operations on resources."),
        ("Neural Networks", "Neural networks are computing systems inspired by biological neural networks. They consist of layers of interconnected nodes that process information and learn patterns from training data."),
        ("Redis Cache", "Redis is an in-memory data store used as a cache, message broker, and queue. It supports data structures like strings, hashes, lists, and sorted sets with very low latency."),
        ("Async Programming", "Asynchronous programming allows programs to perform tasks concurrently without blocking. Python supports async/await syntax for writing non-blocking code with coroutines."),
    ]
    
    for title, content in documents:
        add_document(title, content)
    
    print(f"\nAdded {len(documents)} documents to the vector store.")
    
    # Test semantic search
    print("\n" + "="*60)
    print("SEMANTIC SEARCH TESTS")
    print("="*60)
    
    answer_with_context("How do I store data that needs fast retrieval?")
    print("\n" + "-"*60)
    answer_with_context("What technology helps run apps consistently across environments?")
    print("\n" + "-"*60)
    answer_with_context("How do computers learn from examples?")