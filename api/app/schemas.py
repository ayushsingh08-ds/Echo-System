from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SensorPayload(BaseModel):
    device_id: str
    device_type: str
    timestamp: datetime
    temperature: Optional[float] = None
    vibration: Optional[float] = None
    rpm: Optional[float] = None
    humidity: Optional[float] = None
    label: Optional[int] = None

class IngestResponse(BaseModel):
    inserted_count: int
