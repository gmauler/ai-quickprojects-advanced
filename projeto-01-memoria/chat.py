import anthropic
import os
import psycopg2
import uuid

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "aidb",
    "user": "postgres",
    "password": "password123"
}

def connect():
    return psycopg2.connect(**DB_CONFIG)

def create_tables():
    """Create the conversations table if it doesn't exist."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(100) NOT NULL,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_session 
        ON conversations(session_id, created_at)
    """)
    conn.commit()
    cur.close()
    conn.close()

def save_message(session_id: str, user_id: str, role: str, content: str):
    """Persist a single message to the database."""
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (session_id, user_id, role, content) VALUES (%s, %s, %s, %s)",
        (session_id, user_id, role, content)
    )
    conn.commit()
    cur.close()
    conn.close()

def load_history(session_id: str, limit: int = 20) -> list:
    """Load the last N messages for a given session."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT role, content FROM conversations 
        WHERE session_id = %s 
        ORDER BY created_at DESC 
        LIMIT %s
    """, (session_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def list_sessions(user_id: str) -> list:
    """List all sessions for a given user."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT session_id, MIN(created_at), COUNT(*) 
        FROM conversations 
        WHERE user_id = %s 
        GROUP BY session_id 
        ORDER BY MIN(created_at) DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def chat(user_id: str, session_id: str = None):
    """Start or resume a chat session with persistent memory."""
    if not session_id:
        session_id = str(uuid.uuid4())
        print(f"New session: {session_id[:8]}...")
    else:
        print(f"Resuming session: {session_id[:8]}...")

    history = load_history(session_id)
    print(f"Previous messages loaded: {len(history)}")
    print("\nCommands: /quit, /new, /sessions, /clear")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ").strip()

        if user_input == "/quit":
            print(f"Session saved: {session_id[:8]}")
            break

        if user_input == "/new":
            print("Starting new session...")
            return chat(user_id)

        if user_input == "/sessions":
            sessions = list_sessions(user_id)
            print(f"\nSessions for {user_id}:")
            for s in sessions:
                print(f"  {s[0][:8]}... | {s[1].strftime('%d/%m %H:%M')} | {s[2]} messages")
            continue

        if user_input == "/clear":
            conn = connect()
            cur = conn.cursor()
            cur.execute("DELETE FROM conversations WHERE session_id = %s", (session_id,))
            conn.commit()
            cur.close()
            conn.close()
            history = []
            print("History cleared!")
            continue

        if not user_input:
            continue

        save_message(session_id, user_id, "user", user_input)
        history.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=f"The user's name is {user_id}. Always remember their name and previous context.",
            messages=history
        )

        reply = response.content[0].text
        save_message(session_id, user_id, "assistant", reply)
        history.append({"role": "assistant", "content": reply})

        print(f"\nClaude: {reply}")

if __name__ == "__main__":
    create_tables()
    user_id = input("Your name: ").strip() or "user"
    chat(user_id)