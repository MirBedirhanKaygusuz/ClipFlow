"""Application configuration — loaded from .env"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Storage
    storage_path: str = "/tmp/clipflow"
    r2_endpoint: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = "clipflow"

    # AI Services
    whisper_api_key: str = ""

    # Processing
    max_upload_size_mb: int = 500
    ffmpeg_preset: str = "fast"
    silence_threshold_db: int = -30
    min_silence_duration: float = 0.3
    max_concurrent_jobs: int = 3

    # Push Notifications
    apns_key_path: str = ""
    apns_key_id: str = ""
    apns_team_id: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
