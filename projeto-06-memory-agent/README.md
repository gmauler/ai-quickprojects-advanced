# Project 06 — Episodic Memory Agent

An AI agent that learns structured facts about users across conversations
and uses that knowledge to personalise every future interaction.

## What I learned
- The difference between conversation memory and episodic memory
- Using Claude to extract structured facts from raw conversations
- Injecting memory into system prompts for personalised responses
- Building a user knowledge graph in PostgreSQL
- How production AI assistants like Copilot maintain user context

## How it works
Session ends
↓
Claude analyses full conversation
↓ extracts structured facts as JSON
[professional] Senior PM at Microsoft
[location] Based in Lisbon
↓ stored in user_facts table
Next session starts
↓
Load all facts for user
↓ inject into system prompt
"What you know about this user: ..."
↓
Personalised responses from the first message

## Prerequisites

- Docker running PostgreSQL
- `ANTHROPIC_API_KEY` environment variable set

## Setup

```bash
pip install anthropic psycopg2-binary
python agent.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/quit` | Extract facts and save memory |
| `/memory` | Show all stored facts |
| `/clear` | Delete all memory for this user |

## Stack

`Python` · `PostgreSQL` · `psycopg2` · `Anthropic API`