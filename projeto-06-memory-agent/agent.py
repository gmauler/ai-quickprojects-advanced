import anthropic
import os
import psycopg2
import json
import uuid
from datetime import datetime

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DB_CONFIG = {
    "host": "localhost", "port": 5432,
    "database": "aidb", "user": "postgres", "password": "password123"
}

def connect():
    return psycopg2.connect(**DB_CONFIG)

def create_tables():
    """
    Two tables:
    - user_facts: structured facts extracted from conversations
    - conversations: raw message history per session
    """
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_facts (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            category VARCHAR(50) NOT NULL,
            fact TEXT NOT NULL,
            confidence FLOAT DEFAULT 1.0,
            source_session VARCHAR(36),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
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
    conn.commit()
    cur.close()
    conn.close()

def load_user_facts(user_id: str) -> list:
    """Load all known facts about a user."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT category, fact, confidence 
        FROM user_facts 
        WHERE user_id = %s 
        ORDER BY updated_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"category": r[0], "fact": r[1], "confidence": r[2]} for r in rows]

def save_fact(user_id: str, category: str, fact: str, 
              confidence: float, session_id: str):
    """Save or update a fact about the user."""
    conn = connect()
    cur = conn.cursor()
    # Check if similar fact already exists in this category
    cur.execute("""
        SELECT id FROM user_facts 
        WHERE user_id = %s AND category = %s AND fact = %s
    """, (user_id, category, fact))
    existing = cur.fetchone()

    if existing:
        # Update confidence and timestamp
        cur.execute("""
            UPDATE user_facts 
            SET confidence = %s, updated_at = NOW()
            WHERE id = %s
        """, (confidence, existing[0]))
    else:
        cur.execute("""
            INSERT INTO user_facts 
            (user_id, category, fact, confidence, source_session)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, category, fact, confidence, session_id))

    conn.commit()
    cur.close()
    conn.close()

def extract_facts(conversation: list, user_id: str, session_id: str):
    """
    Use Claude to analyse the conversation and extract structured facts.
    Only runs at the end of each session to avoid excessive API calls.
    """
    if len(conversation) < 2:
        return

    # Format conversation for analysis
    conv_text = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}" 
        for msg in conversation
    ])

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""Analyse this conversation and extract facts about the user.
Return ONLY a JSON array. Each fact must have:
- category: one of [personal, professional, preferences, goals, skills, location]
- fact: a clear, concise statement
- confidence: 0.0 to 1.0 based on how certain the fact is

Only extract facts explicitly stated or strongly implied.
Return [] if no clear facts found.

Conversation:
{conv_text}

Return only the JSON array, no other text."""
        }]
    )

    try:
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        facts = json.loads(text)
        
        if facts:
            print(f"\n  Extracted {len(facts)} facts from conversation:")
            for fact in facts:
                save_fact(
                    user_id, 
                    fact["category"], 
                    fact["fact"],
                    fact.get("confidence", 0.8),
                    session_id
                )
                print(f"    [{fact['category']}] {fact['fact']}")

    except (json.JSONDecodeError, KeyError) as e:
        print(f"  Could not parse facts: {e}")

def build_system_prompt(user_id: str) -> str:
    """
    Build a personalised system prompt by injecting known facts about the user.
    This is the core of episodic memory — past knowledge shapes future responses.
    """
    facts = load_user_facts(user_id)

    if not facts:
        return """You are a helpful assistant with memory capabilities.
Pay attention to what the user shares about themselves — 
you will remember it for future conversations."""

    # Group facts by category for cleaner injection
    grouped = {}
    for f in facts:
        cat = f["category"]
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(f["fact"])

    memory_text = "\n".join([
        f"  {cat.upper()}: {', '.join(facts_list)}"
        for cat, facts_list in grouped.items()
    ])

    return f"""You are a helpful assistant with episodic memory.

What you know about this user:
{memory_text}

Use this knowledge naturally in your responses — personalise recommendations,
reference their background when relevant, but don't repeat facts unnecessarily.
Pay attention to new information they share and build on what you already know."""

def save_message(session_id: str, user_id: str, role: str, content: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (session_id, user_id, role, content) VALUES (%s, %s, %s, %s)",
        (session_id, user_id, role, content)
    )
    conn.commit()
    cur.close()
    conn.close()

def chat(user_id: str):
    """Main chat loop with episodic memory."""
    session_id = str(uuid.uuid4())
    conversation = []

    # Load and display existing memory
    facts = load_user_facts(user_id)
    if facts:
        print(f"\nMemory loaded — {len(facts)} facts known about {user_id}:")
        for f in facts[:5]:  # show first 5
            print(f"  [{f['category']}] {f['fact']}")
        if len(facts) > 5:
            print(f"  ... and {len(facts) - 5} more")
    else:
        print(f"\nNo previous memory found for {user_id}. Starting fresh.")

    print("\nCommands: /quit (saves memory), /memory (show all facts), /clear")
    print("-" * 55)

    while True:
        user_input = input("\nYou: ").strip()

        if user_input == "/quit":
            print("\nExtracting facts from this conversation...")
            extract_facts(conversation, user_id, session_id)
            print("Memory saved. Goodbye!")
            break

        if user_input == "/memory":
            facts = load_user_facts(user_id)
            if not facts:
                print("No facts stored yet.")
            else:
                print(f"\nAll known facts about {user_id}:")
                for f in facts:
                    print(f"  [{f['category']}] {f['fact']} (confidence: {f['confidence']:.1f})")
            continue

        if user_input == "/clear":
            conn = connect()
            cur = conn.cursor()
            cur.execute("DELETE FROM user_facts WHERE user_id = %s", (user_id,))
            conn.commit()
            cur.close()
            conn.close()
            print("Memory cleared!")
            continue

        if not user_input:
            continue

        # Build personalised system prompt with current memory
        system_prompt = build_system_prompt(user_id)

        save_message(session_id, user_id, "user", user_input)
        conversation.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            messages=conversation
        )

        reply = response.content[0].text
        save_message(session_id, user_id, "assistant", reply)
        conversation.append({"role": "assistant", "content": reply})

        print(f"\nClaude: {reply}")

if __name__ == "__main__":
    create_tables()
    user_id = input("Your name: ").strip() or "user"
    chat(user_id)