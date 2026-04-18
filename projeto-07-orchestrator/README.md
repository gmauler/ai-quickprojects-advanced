# Project 07 — Multi-Agent Orchestrator

An orchestration system that routes tasks to specialised AI agents
and synthesises their outputs into a single coherent response.

## What I learned
- The orchestrator pattern for multi-agent systems
- How specialised system prompts create expert agents
- Using Claude to make routing decisions dynamically
- Sequential agent chaining — each agent builds on previous results
- Result synthesis to produce unified, high-quality outputs

## How it works
User task
↓
Orchestrator analyses task
↓ Claude decides which agents to use
["researcher", "writer"]
↓
Agent 1 (Researcher) runs on original task
↓ result passed as context
Agent 2 (Writer) runs with research context
↓
Synthesiser combines outputs
↓
Single cohesive response

## Available agents

| Agent | Best for |
|-------|----------|
| Researcher | Factual questions, topic analysis, background research |
| Coder | Writing functions, code reviews, technical implementations |
| Writer | Blog posts, emails, documentation, summaries |
| Analyst | Data interpretation, strategy, decision support |

## Setup

```bash
pip install anthropic
python orchestrator.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/agents` | List all available agents |
| `/quit` | Exit |

## Stack

`Python` · `Anthropic API` · `dataclasses`