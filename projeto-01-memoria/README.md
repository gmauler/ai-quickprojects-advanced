# Project 01 — Persistent Memory Chat

A terminal chatbot that remembers conversations across sessions using PostgreSQL.
Unlike a standard chatbot, this one persists every message to a database —
close the terminal, come back days later, and it picks up exactly where you left off.

## What I learned
- Connecting Python to PostgreSQL with psycopg2
- Designing a conversations table with sessions and users
- Loading and injecting conversation history into the Claude API
- The difference between stateless LLMs and stateful applications

## How it works
User input
↓
Load history from PostgreSQL (last 20 messages)
↓
Send full history to Claude API
↓
Save new messages to PostgreSQL
↓
Display response

## Prerequisites

- Docker running PostgreSQL:
```bash
  docker run --name postgres-ai -e POSTGRES_PASSWORD=password123 \
    -e POSTGRES_DB=aidb -p 5432:5432 -d postgres:16
```
- `ANTHROPIC_API_KEY` environment variable set

## Setup

```bash
pip install anthropic psycopg2-binary
python chat.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/quit` | Save and exit |
| `/new` | Start a new session |
| `/sessions` | List all past sessions |
| `/clear` | Clear current session history |

## Stack

`Python` · `PostgreSQL` · `psycopg2` · `Anthropic API`