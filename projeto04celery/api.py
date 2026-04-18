from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from projeto04celery.tasks import process_document, process_multiple, app as celery_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SingleRequest(BaseModel):
    text: str
    instruction: str = "Summarise this document in 3 key points"

class MultipleRequest(BaseModel):
    texts: list[str]
    instruction: str = "Summarise in 1 sentence"

@app.post("/process")
def process(request: SingleRequest):
    """
    Submit a document for async processing.
    Returns a job_id immediately — poll /status/{job_id} for progress.
    """
    task = process_document.delay(request.text, request.instruction)
    return {
        "job_id": task.id,
        "status": "PENDING",
        "message": "Task created. Poll /status/{job_id} for updates."
    }

@app.post("/process-multiple")
def process_multiple_docs(request: MultipleRequest):
    """Submit multiple documents for sequential async processing."""
    task = process_multiple.delay(request.texts, request.instruction)
    return {"job_id": task.id, "status": "PENDING"}

@app.get("/status/{job_id}")
def status(job_id: str):
    """Poll the status and result of an async task."""
    result = celery_app.AsyncResult(job_id)

    try:
        if result.state == "PENDING":
            return {"job_id": job_id, "state": "PENDING", "progress": 0}

        elif result.state in ("STARTED", "PROGRESS"):
            info = result.info or {}
            return {
                "job_id": job_id,
                "state": result.state,
                "progress": info.get("progress", 0),
                "message": info.get("message", "")
            }

        elif result.state == "SUCCESS":
            data = result.result or {}
            return {
                "job_id": job_id,
                "state": "SUCCESS",
                "progress": 100,
                "result": data.get("result", str(data))
            }

        elif result.state == "FAILURE":
            return {"job_id": job_id, "state": "FAILURE", "error": str(result.info)}

        return {"job_id": job_id, "state": result.state}

    except Exception as e:
        return {"job_id": job_id, "state": "ERROR", "detail": str(e)}

@app.get("/jobs")
def list_jobs():
    """See all jobs in the Flower dashboard."""
    return {"message": "Visit http://localhost:5555 to monitor all jobs"}