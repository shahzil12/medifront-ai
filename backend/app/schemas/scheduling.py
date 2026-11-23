from pydantic import BaseModel
from datetime import time, datetime, date
from typing import Optional

class WorkingHoursCreate(BaseModel):
    weekday: int  # 0 = Monday ... 6 = Sunday
    start_time: time  # e.g., "09:00:00"
    end_time: time    # e.g., "14:00:00"
    slot_minutes: int = 30

class BlockedTimeCreate(BaseModel):
    start_at: datetime  # e.g., "2026-11-26T11:00:00"
    end_at: datetime    # e.g., "2026-11-26T12:00:00"
    reason: Optional[str] = "Personal Break"

class AppointmentBookRequest(BaseModel):
    doctor_id: int
    slot_start: datetime  # e.g., "2026-11-26T09:30:00"
    channel: str = "Web"

class AppointmentRescheduleRequest(BaseModel):
    new_slot_start: datetime