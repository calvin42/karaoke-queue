from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class QueueStatusEnum(str, Enum):
    waiting = "waiting"
    singing = "singing"
    done = "done"


class QueueEntryCreate(BaseModel):
    singer: str
    song: str


class QueueEntry(BaseModel):
    id: int
    singer: str
    song: str
    status: QueueStatusEnum
    position: int
    created_at: datetime

    model_config = {"from_attributes": True}


class QueueListResponse(BaseModel):
    queue: list[QueueEntry]
