# FastAPI Backend Patterns — ClipFlow

## Proje Setup
```bash
pip install fastapi uvicorn python-multipart pydantic boto3 structlog
```

## App Yapısı
```python
# app/main.py
from fastapi import FastAPI
from app.api.routes import upload, process
from app.config import settings

app = FastAPI(title="ClipFlow API", version="0.1.0")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(process.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

## Config Pattern
```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    r2_endpoint: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = "clipflow"
    whisper_api_key: str = ""
    apns_key_path: str = ""
    max_upload_size_mb: int = 500
    ffmpeg_preset: str = "fast"

    class Config:
        env_file = ".env"

settings = Settings()
```

## Pydantic Models
```python
# app/models/job.py
from pydantic import BaseModel
from enum import Enum

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    AWAITING_DECISION = "awaiting_decision"
    DONE = "done"
    FAILED = "failed"

class ProcessRequest(BaseModel):
    clip_ids: list[str]
    mode: str = "talking_reels"  # talking_reels | music_edit
    settings: dict = {"output_format": "9:16", "add_captions": True}
    device_token: str | None = None

class ProcessResponse(BaseModel):
    job_id: str
    estimated_seconds: int

class StatusResponse(BaseModel):
    status: JobStatus
    progress: int = 0
    step: str = ""
    output_url: str | None = None
    question: str | None = None
    options: list[str] | None = None
```

## Upload Endpoint
```python
# app/api/routes/upload.py
from fastapi import APIRouter, UploadFile, HTTPException
from uuid import uuid4
import aiofiles

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile):
    if not file.filename.endswith((".mp4", ".mov", ".m4v")):
        raise HTTPException(400, "Sadece MP4/MOV/M4V destekleniyor")

    file_id = str(uuid4())
    path = f"/tmp/clipflow/{file_id}.mp4"

    async with aiofiles.open(path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            await f.write(chunk)

    # V2'de R2'ye yükle
    return {"file_id": file_id}
```

## Error Handling Pattern
```python
# app/exceptions.py
from fastapi import HTTPException

class ClipFlowError(Exception):
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code

class VideoTooLargeError(ClipFlowError):
    def __init__(self, size_mb: float):
        super().__init__(f"Video çok büyük: {size_mb:.0f}MB (maks 500MB)", 413)

class FFmpegError(ClipFlowError):
    def __init__(self, stderr: str):
        super().__init__(f"FFmpeg hatası: {stderr[:200]}", 500)

class ProcessingTimeoutError(ClipFlowError):
    def __init__(self, job_id: str):
        super().__init__(f"İşleme zaman aşımı: {job_id}", 504)
```

## Logging Pattern
```python
# app/logging.py
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
log = structlog.get_logger()

# Kullanım:
log.info("video_processing_started", job_id=job_id, clip_count=len(clips))
log.error("ffmpeg_failed", job_id=job_id, error=stderr[:200])
```

## R2 Storage (V2)
```python
# app/services/storage.py
import boto3
from app.config import settings

s3 = boto3.client("s3",
    endpoint_url=settings.r2_endpoint,
    aws_access_key_id=settings.r2_access_key,
    aws_secret_access_key=settings.r2_secret_key
)

async def upload_to_r2(local_path: str, key: str) -> str:
    s3.upload_file(local_path, settings.r2_bucket, key)
    return f"https://{settings.r2_bucket}.r2.dev/{key}"

async def get_presigned_url(key: str, expires: int = 3600) -> str:
    return s3.generate_presigned_url("get_object",
        Params={"Bucket": settings.r2_bucket, "Key": key},
        ExpiresIn=expires)
```

## Test Pattern
```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_video(tmp_path):
    """1 saniyelik test videosu oluştur"""
    path = tmp_path / "test.mp4"
    subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=1920x1080",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(path)
    ], check=True, capture_output=True)
    return path
```
