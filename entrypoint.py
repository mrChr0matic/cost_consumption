from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/estimate")
def estimate(req: EstimateRequest):
    if not req.image_uris and not req.file_uris:
        raise HTTPException(
            status_code=400,
            detail="At least one of image_uris or file_uris must be provided"
        )
    if not req.client_name or not req.use_case_name:
        raise HTTPException(
            status_code=400,
            detail="client_name and use_case_name are required"
        )
    try:
        result = run_llm_pipeline(
            image_uris=req.image_uris,
            file_uris=req.file_uris,
            client_name=req.client_name,
            use_case_name=req.use_case_name,
            markets=req.markets,
            global_consumption_multiplier=req.global_consumption_multiplier,
            user_prompt=req.user_prompt,
            budget=req.budget
        )
        return result  # {"drive_link": "..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))