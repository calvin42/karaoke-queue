from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone
import enum

Base = declarative_base()


class QueueStatusEnum(str, enum.Enum):
    waiting = "waiting"
    singing = "singing"
    done = "done"


class QueueEntry(Base):
    __tablename__ = "queue"

    id = Column(Integer, primary_key=True, index=True)
    singer = Column(String, nullable=False)
    song = Column(String, nullable=False)
    status = Column(Enum(QueueStatusEnum), default=QueueStatusEnum.waiting, nullable=False)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
