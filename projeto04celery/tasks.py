import anthropic
import os
import time
from celery import Celery

# Celery app with Redis as both broker and result backend
# broker — where tasks are queued
# backend — where results are stored after execution
app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/London",
    task_track_started=True  # enables STARTED state tracking
)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

@app.task(bind=True)
def process_document(self, text: str, instruction: str):
    """
    Process a document with Claude asynchronously.
    Reports progress at each stage so the caller can poll for updates.

    Args:
        text: The document content to process
        instruction: The instruction to give Claude (e.g. "Summarize in 3 points")

    Returns:
        dict with result text, token count, and final progress
    """
    try:
        self.update_state(
            state="STARTED",
            meta={"progress": 0, "message": "Initialising..."}
        )
        time.sleep(1)

        self.update_state(
            state="PROGRESS",
            meta={"progress": 30, "message": "Analysing document..."}
        )
        time.sleep(1)

        self.update_state(
            state="PROGRESS",
            meta={"progress": 60, "message": "Processing with Claude..."}
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": f"{instruction}\n\nDocument:\n{text}"
            }]
        )

        self.update_state(
            state="PROGRESS",
            meta={"progress": 90, "message": "Finalising..."}
        )
        time.sleep(0.5)

        return {
            "progress": 100,
            "message": "Done!",
            "result": response.content[0].text,
            "tokens": response.usage.input_tokens + response.usage.output_tokens
        }

    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise

@app.task(bind=True)
def process_multiple(self, texts: list, instruction: str):
    """
    Process multiple documents sequentially with progress tracking.

    Args:
        texts: List of document strings to process
        instruction: Instruction applied to each document

    Returns:
        dict with list of results and total count
    """
    results = []
    total = len(texts)

    for i, text in enumerate(texts):
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": int((i / total) * 100),
                "message": f"Processing document {i+1} of {total}..."
            }
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": f"{instruction}\n\n{text}"}]
        )
        results.append(response.content[0].text)
        time.sleep(0.5)

    return {
        "progress": 100,
        "message": "All documents processed!",
        "results": results,
        "total_processed": total
    }