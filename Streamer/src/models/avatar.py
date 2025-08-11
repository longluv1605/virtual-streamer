from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
)

from pydantic import BaseModel

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from .models import Base


class Avatar(Base):
    __tablename__ = "avatars"

    id = Column(Integer, primary_key=True, index=True)
    video_path = Column(String(500), nullable=False, unique=True)  # Unique video path
    name = Column(String(255), nullable=False)  # Friendly name
    is_prepared = Column(Boolean, default=False)  # Đã preparation chưa
    bbox_shift = Column(Integer, default=0)  # Avatar-specific bbox_shift
    preparation_status = Column(
        String(50), default="pending"
    )  # pending, processing, completed, error
    file_size = Column(Integer)  # File size in bytes
    duration = Column(Float)  # Video duration in seconds
    resolution = Column(String(20))  # Video resolution (e.g., "1920x1080")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    stream_sessions = relationship("StreamSession", back_populates="avatar")


class AvatarCreate(BaseModel):
    video_path: str
    name: str
    bbox_shift: int = 0


class AvatarUpdate(BaseModel):
    name: Optional[str] = None
    bbox_shift: Optional[int] = None
    is_prepared: Optional[bool] = None
    preparation_status: Optional[str] = None


class AvatarResponse(BaseModel):
    id: int
    video_path: str
    name: str
    is_prepared: bool
    bbox_shift: int
    preparation_status: str
    file_size: Optional[int]
    duration: Optional[float]
    resolution: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

