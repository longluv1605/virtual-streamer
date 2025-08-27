from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    CheckConstraint
)

from pydantic import BaseModel, ConfigDict, model_validator
    
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from .models import Base


class Avatar(Base):
    __tablename__ = "avatars"

    id = Column(Integer, primary_key=True, index=True)
    # video_path = Column(String(500), nullable=False, unique=True)  # Unique video path
    video_path = Column(String(500), nullable=False)  # Unique video path
    name = Column(String(255), nullable=False)  # Friendly name
    is_prepared = Column(Boolean, default=False)  # Đã preparation chưa
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    default = Column(Boolean, default=False) # True if avatar is system default
    compress = Column(Boolean, default=False) # True if user wanna preprocess avatar
    
    # Constraint
    compress_fps = Column(Integer, nullable=True)
    compress_resolution = Column(Integer, nullable=True)
    compress_bitrate = Column(Integer, nullable=True)

    __table_args__ = (
        # If compress = TRUE, 3 field must NOT NULL
        CheckConstraint(
            "NOT compress OR (compress_fps IS NOT NULL AND compress_resolution IS NOT NULL AND compress_bitrate IS NOT NULL)",
            name="compress_true_requires_fields",
        ),
        # If compress = FALSE, 3 field must NULL
        CheckConstraint(
            "compress OR (compress_fps IS NULL AND compress_resolution IS NULL AND compress_bitrate IS NULL)",
            name="compress_false_requires_null_fields",
        ),
        # (Option) value range
        CheckConstraint(
            "compress = 0 OR (compress_fps > 0 AND compress_bitrate > 0 AND compress_resolution > 0)",
            name="compress_positive_values",
        ),
    )
        
    # Relationships
    stream_sessions = relationship("StreamSession", back_populates="avatar")


class AvatarCreate(BaseModel):
    # từ chối field lạ gửi lên
    model_config = ConfigDict(from_attributes=False, extra='forbid')

    video_path: str
    name: str

    # cấu hình nén
    compress: bool = False
    compress_fps: Optional[int] = None
    compress_resolution: Optional[int] = None
    compress_bitrate: Optional[int] = None

    @model_validator(mode='after')
    def validate_compress(self):
        if self.compress:
            for k in ('compress_fps', 'compress_resolution', 'compress_bitrate'):
                v = getattr(self, k)
                if v is None:
                    raise ValueError(f'{k} is required when compress=True')
                if v <= 0:
                    raise ValueError(f'{k} must be > 0')
        else:
            # đảm bảo dữ liệu sạch khi tắt nén
            self.compress_fps = None
            self.compress_resolution = None
            self.compress_bitrate = None
        return self



class AvatarUpdate(BaseModel):
    name: Optional[str] = None


class AvatarResponse(BaseModel):
    id: int
    video_path: str
    name: str
    is_prepared: bool
    created_at: datetime
    updated_at: datetime
    default: bool
    
    class Config:
        from_attributes = True
