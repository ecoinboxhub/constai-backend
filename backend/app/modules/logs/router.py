from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class LogCreate(BaseModel):
    project_id: str
    log_text: str

class MobileTelemetryIn(BaseModel):
    sync_latency_ms: Optional[int] = 0
    upload_failures: Optional[int] = 0
    retry_count: Optional[int] = 0
    offline_duration_seconds: Optional[float] = 0.0
    battery_level: Optional[float] = 1.0
    queue_size: Optional[int] = 0
    device_platform: Optional[str] = "unknown"

@router.post("")
def create_log(log: LogCreate):
    # Mocking log creation for MVP
    return {"status": "success", "detail": "Log created successfully", "data": log.dict()}

@router.get("")
def get_logs():
    return []

@router.post("/mobile-telemetry")
def submit_mobile_telemetry(payload: MobileTelemetryIn):
    # Process and log telemetry events asynchronously
    import logging
    logger = logging.getLogger("constai.telemetry")
    logger.info(f"Telemetry payload received from {payload.device_platform} device: sync_latency={payload.sync_latency_ms}ms, queue_size={payload.queue_size}, battery={payload.battery_level * 100}%")
    return {"status": "success", "detail": "Telemetry record registered."}

