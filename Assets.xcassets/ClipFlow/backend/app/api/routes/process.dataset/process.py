"""Video processing endpoints."""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from uuid import uuid4

from app.models.job import ProcessRequest, ProcessResponse, StatusResponse, JobStatus
from app.services.job_manager import job_store
from app.workers.talking_reels import process_talking_reels
from app.workers.musical_edit import process_musical_edit

router = APIRouter()


@router.post("/process", response_model=ProcessResponse)
async def start_processing(request: ProcessRequest, background_tasks: BackgroundTasks):
    """Start video processing. Returns job_id for polling."""

    job_id = str(uuid4())
    job_store[job_id] = {
        "status": JobStatus.QUEUED,
        "progress": 0,
        "step": "queued",
    }

    # Dispatch to appropriate worker
    if request.mode == "talking_reels":
        background_tasks.add_task(process_talking_reels, job_id, request)
    elif request.mode == "musical_edit":
        background_tasks.add_task(process_musical_edit, job_id, request)
    else:
        raise HTTPException(400, f"Bilinmeyen mod: {request.mode}")

    return ProcessResponse(job_id=job_id, estimated_seconds=90)


@router.get("/process/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    """Poll job status."""

    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job bulunamadı")

    return StatusResponse(**job)


@router.post("/process/{job_id}/decision")
async def submit_decision(job_id: str, choice: int):
    """Submit binary decision for a job."""

    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job bulunamadı")
    if job["status"] != JobStatus.AWAITING_DECISION:
        raise HTTPException(400, "Bu job karar beklemiyior")

    job["decision"] = choice
    job["status"] = JobStatus.PROCESSING
    return {"status": "ok"}
