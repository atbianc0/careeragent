from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApplicationEventRead(BaseModel):
    id: int
    job_id: int
    event_type: str
    event_time: datetime
    notes: str

    model_config = ConfigDict(from_attributes=True)

