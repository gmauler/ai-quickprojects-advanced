# Project 10 — Intelligent Monitoring Agent

A monitoring agent that watches URLs for changes and uses Claude
to determine if changes are relevant before sending alerts.
Eliminates alert noise by filtering out meaningless changes.

## What I learned
- Scheduling periodic tasks with APScheduler
- Content hashing for efficient change detection
- Using LLMs to filter signal from noise in monitoring
- The difference between detecting a change and understanding it
- Building intelligent alerting vs. naive threshold alerting

## How it works
Scheduler triggers check
↓
Fetch URL → extract text → hash content
↓ hash unchanged → skip (no API call)
↓ hash changed
Claude analyses old vs new content
↓ noise (timestamps, counters) → skip
↓ relevant (incidents, announcements, docs)
Send email alert with summary + urgency
Store snapshot in PostgreSQL

## Real-world application
Monitor automatically:
- Service status pages for your components
- Internal documentation for updates
- Changelog pages for dependencies
- Incident management dashboards

## Prerequisites
- Docker running PostgreSQL
- `ANTHROPIC_API_KEY` environment variable set
- Optional for email alerts:
```bash
  SMTP_EMAIL=your@gmail.com
  SMTP_PASSWORD=your_app_password
  ALERT_EMAIL=destination@email.com
```

## Setup

```bash
pip install anthropic apscheduler requests psycopg2-binary
python agent.py
```

## Stack

`Python` · `APScheduler` · `PostgreSQL` · `requests` · `Anthropic API`