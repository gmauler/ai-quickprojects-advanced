# Project 08 — Code Execution Agent

An AI agent that writes Python code, executes it in an isolated Docker sandbox,
analyses the output, and iterates until the solution works correctly.

## What I learned
- Building an agentic loop with tool use and iterative feedback
- Running untrusted code safely in Docker containers
- How agents reason about errors and self-correct
- The difference between a one-shot code generator and an iterative coding agent
- Resource limiting containers (memory, CPU, network)

## How it works
Agent receives task
↓
Writes Python code
↓
Calls execute_code tool
↓
Docker runs code in isolated container
(no network, 128MB RAM, 0.5 CPU)
↓ stdout + stderr returned
Agent analyses result
↓ error → fix and retry (max 5 attempts)
↓ success → explain solution
Final answer

## Prerequisites

- Docker Desktop running
- `ANTHROPIC_API_KEY` environment variable set

```bash
docker pull python:3.11-slim
```

## Setup

```bash
pip install anthropic
python agent.py
```

## Stack

`Python` · `Docker` · `Anthropic API (tool use)` · `subprocess`