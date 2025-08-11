from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
)

from pydantic import BaseModel

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from .models import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("stream_sessions.id"), nullable=False)
    username = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    is_question = Column(Boolean, default=False)  # Đánh dấu là câu hỏi cần trả lời
    answered = Column(Boolean, default=False)
    answer_video_path = Column(String(500), nullable=True)  # Đường dẫn video trả lời

    # Relationship
    session = relationship("StreamSession", back_populates="comments")


class CommentCreate(BaseModel):
    username: str
    message: str
    is_question: bool = False


class CommentResponse(BaseModel):
    id: int
    username: str
    message: str
    timestamp: datetime
    is_question: bool
    answered: bool
    answer_video_path: Optional[str] = None

    class Config:
        from_attributes = True
