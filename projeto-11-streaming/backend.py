import anthropic
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]
    system: str = "You are a helpful assistant."

def stream_response(messages: list, system: str):
    """
    Generator function that yields SSE-formatted chunks.
    
    SSE format: each chunk is "data: {text}\n\n"
    The client reads these as a stream of events.
    A special "data: [DONE]\n\n" signals the end.
    """
    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system,
        messages=[{"role": m["role"], "content": m["content"]} for m in messages]
    ) as stream:
        for text in stream.text_stream:
            # Escape newlines so SSE format is preserved
            chunk = text.replace("\n", "\\n")
            yield f"data: {chunk}\n\n"

    yield "data: [DONE]\n\n"

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Streaming chat endpoint.
    Returns a StreamingResponse with SSE content type.
    """
    messages = [m.model_dump() for m in request.messages]
    return StreamingResponse(
        stream_response(messages, request.system),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # disables nginx buffering
        }
    )

@app.get("/health")
def health():
    return {"status": "ok"}