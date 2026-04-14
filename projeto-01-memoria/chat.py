import anthropic
import os
import psycopg2
import uuid
from datetime import datetime

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "aidb",
    "user": "postgres",
    "password": "password123"
}

def conectar():
    return psycopg2.connect(**DB_CONFIG)

def criar_tabelas():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversas (
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
        ON conversas(session_id, created_at)
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Tabelas criadas!")

def guardar_mensagem(session_id: str, user_id: str, role: str, content: str):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversas (session_id, user_id, role, content) VALUES (%s, %s, %s, %s)",
        (session_id, user_id, role, content)
    )
    conn.commit()
    cur.close()
    conn.close()

def carregar_historico(session_id: str, limite: int = 20) -> list:
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT role, content FROM conversas 
        WHERE session_id = %s 
        ORDER BY created_at DESC 
        LIMIT %s
    """, (session_id, limite))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def listar_sessoes(user_id: str) -> list:
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT session_id, MIN(created_at), COUNT(*) 
        FROM conversas 
        WHERE user_id = %s 
        GROUP BY session_id 
        ORDER BY MIN(created_at) DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def chat(user_id: str, session_id: str = None):
    if not session_id:
        session_id = str(uuid.uuid4())
        print(f"Nova sessao: {session_id[:8]}...")
    else:
        print(f"A retomar sessao: {session_id[:8]}...")

    historico = carregar_historico(session_id)
    print(f"Mensagens anteriores: {len(historico)}")
    print("\nComandos: /sair, /nova, /sessoes, /limpar")
    print("-" * 50)

    while True:
        user_input = input("\nTu: ").strip()

        if user_input == "/sair":
            print(f"Sessao guardada: {session_id[:8]}")
            break

        if user_input == "/nova":
            print("A iniciar nova sessao...")
            return chat(user_id)

        if user_input == "/sessoes":
            sessoes = listar_sessoes(user_id)
            print(f"\nSessoes de {user_id}:")
            for s in sessoes:
                print(f"  {s[0][:8]}... | {s[1].strftime('%d/%m %H:%M')} | {s[2]} msgs")
            continue

        if user_input == "/limpar":
            conn = conectar()
            cur = conn.cursor()
            cur.execute("DELETE FROM conversas WHERE session_id = %s", (session_id,))
            conn.commit()
            cur.close()
            conn.close()
            historico = []
            print("Historico limpo!")
            continue

        if not user_input:
            continue

        guardar_mensagem(session_id, user_id, "user", user_input)
        historico.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=f"O utilizador chama-se {user_id}. Lembra-te sempre do nome e contexto anterior.",
            messages=historico
        )

        resposta = response.content[0].text
        guardar_mensagem(session_id, user_id, "assistant", resposta)
        historico.append({"role": "assistant", "content": resposta})

        print(f"\nClaude: {resposta}")

if __name__ == "__main__":
    criar_tabelas()
    user_id = input("O teu nome: ").strip() or "gustavo"
    chat(user_id)