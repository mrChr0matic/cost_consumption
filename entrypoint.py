import uuid
import os
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional

from sql_store import write_job_result, get_job_result
from llm.llm import run_llm_pipeline
from llm.adls import upload_to_adls
from summarizer import summarize_user_prompt, summarize_image_file, summarize_document_file

from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from azure.storage.filedatalake import DataLakeServiceClient
from datetime import datetime, timedelta
import io

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


class SummarizePromptRequest(BaseModel):
    user_prompt: str


def run_pipeline_job(job_id: str, req: EstimateRequest):
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



@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Accepts a file, uploads to ADLS, returns the SAS URL and adls_path."""
    filename = file.filename.lower()
    file_bytes = await file.read()

    if filename.endswith((".pdf", ".docx", ".doc")):
        adls_path = f"uploads/pdfs/{file.filename}"
        file_type = "pdf"
    elif filename.endswith((".png", ".jpg", ".jpeg")):
        adls_path = f"uploads/images/{file.filename}"
        file_type = "image"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")

    try:
        url = upload_to_adls(file_bytes, adls_path)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"url": url, "adls_path": adls_path, "file_type": file_type}


@app.post("/summarize/file")
async def summarize_file(file: UploadFile = File(...)):
    """Summarize an uploaded image or PDF directly (no ADLS storage)."""
    filename = file.filename.lower()

    class UploadedFileWrapper:
        def __init__(self, data: bytes, name: str):
            self._buf = io.BytesIO(data)
            self.name = name
        def read(self): return self._buf.read()
        def seek(self, pos): self._buf.seek(pos)

    file_bytes = await file.read()
    wrapped = UploadedFileWrapper(file_bytes, file.filename)

    try:
        if filename.endswith((".pdf", ".docx", ".doc")):
            summary = summarize_document_file(wrapped)
        elif filename.endswith((".png", ".jpg", ".jpeg")):
            summary = summarize_image_file(wrapped)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"summary": summary}


@app.post("/summarize/prompt")
def summarize_prompt(req: SummarizePromptRequest):
    """Summarize structured user prompt text into professional paragraphs."""
    try:
        summary = summarize_user_prompt(req.user_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"summary": summary}