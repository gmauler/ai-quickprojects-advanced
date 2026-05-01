# Project 11 — Streaming Chat UI

A React chat interface with real-time token streaming and switchable AI personas.
Responses appear word-by-word as they are generated, using Server-Sent Events.

## What I learned
- Streaming LLM responses with Server-Sent Events (SSE)
- Reading a ReadableStream in React with the Fetch API
- The difference between useState and useRef for streaming state
- Building switchable system prompts (personas) in the UI
- AsyncGenerator functions in FastAPI for progressive responses

## How it works
User sends message
↓
React POST /chat → receives StreamingResponse
↓
FastAPI opens Anthropic stream
↓ yields "data: {token}\n\n" as each token arrives
React reads chunks via ReadableStream reader
↓ appends each token to the last message
User sees text appearing in real time
Stream ends with "data: [DONE]\n\n"

## Personas

| Persona | System Prompt Focus |
|---------|-------------------|
| Assistant | General purpose helpful assistant |
| Security Expert | Cybersecurity and threat protection |
| PM Coach | Product strategy and stakeholder management |
| KQL Expert | Kusto Query Language queries and optimisation |

## Setup

```bash
# Backend
pip install anthropic fastapi uvicorn
uvicorn projeto-11-streaming.backend:app --reload --port=8002

# Frontend
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173**

## Stack

`Python` · `FastAPI` · `SSE` · `React` · `Anthropic API (streaming)`