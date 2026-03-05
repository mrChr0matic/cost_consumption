import uuid
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

from sql_store import write_job_result, get_job_result
from llm.llm import run_llm_pipeline

app = FastAPI(title="Consumption Estimate API")


class EstimateRequest(BaseModel):
    image_uris: List[str] = []
    file_uris: List[str] = []
    client_name: str
    use_case_name: str
    markets: List[dict] = []
    global_consumption_multiplier: float = 1.0
    user_prompt: Optional[str] = None
    budget: Optional[float] = None


def run_pipeline_job(job_id: str, req: EstimateRequest):
    """Runs in a background thread. Writes result to SQLite when done."""
    try:
        result = run_llm_pipeline(
            image_uris=req.image_uris,
            file_uris=req.file_uris,
            client_name=req.client_name,
            use_case_name=req.use_case_name,
            markets=req.markets,
            global_consumption_multiplier=req.global_consumption_multiplier,
            user_prompt=req.user_prompt,
            budget=req.budget,
        )
        write_job_result(job_id, status="done", drive_link=result["drive_link"])
    except Exception as e:
        write_job_result(job_id, status="error", error=str(e))


@app.post("/estimate")
def estimate(req: EstimateRequest, background_tasks: BackgroundTasks, request: Request):
    client_host = request.client.host
    if client_host not in ("127.0.0.1", "::1"):
        auth_header = request.headers.get("Authorization", "")
        user_token = (
            request.headers.get("X-Forwarded-Access-Token")
            or auth_header.replace("Bearer ", "").strip()
        )
        if not user_token:
            raise HTTPException(status_code=401, detail="Missing user token")

    if not req.client_name or not req.use_case_name:
        raise HTTPException(status_code=400, detail="client_name and use_case_name are required")

    job_id = str(uuid.uuid4())
    write_job_result(job_id, status="pending")
    background_tasks.add_task(run_pipeline_job, job_id, req)
    return {"job_id": job_id}


@app.get("/status/{job_id}")
def get_status(job_id: str):
    job = get_job_result(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/health")
def health():
    return {"status": "ok"}