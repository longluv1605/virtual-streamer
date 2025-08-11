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
from typing import List, Optional

from .avatar import AvatarResponse
from .product import ProductResponse

from .models import Base


class StreamSession(Base):
    __tablename__ = "stream_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(
        String(50), default="preparing"
    )  # preparing, ready, live, completed
    avatar_id = Column(
        Integer, ForeignKey("avatars.id"), nullable=False
    )  # Reference to Avatar
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    avatar = relationship("Avatar", back_populates="stream_sessions")
    stream_products = relationship(
        "StreamProduct", back_populates="session", cascade="all, delete-orphan"
    )
    comments = relationship(
        "Comment", back_populates="session", cascade="all, delete-orphan"
    )


class StreamProduct(Base):
    __tablename__ = "stream_products"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("stream_sessions.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    order_in_stream = Column(Integer, nullable=False)  # Thứ tự xuất hiện trong stream
    script_text = Column(Text)  # Script được tạo bởi LLM
    audio_path = Column(String(500))  # Path to generated audio
    video_path = Column(String(500))  # Path to generated video (MuseTalk output)
    duration_seconds = Column(Integer, default=60)  # Thời gian nói về sản phẩm
    is_processed = Column(Boolean, default=False)  # Đã xử lý xong chưa
    created_at = Column(DateTime, default=func.now())

    # Relationships
    session = relationship("StreamSession", back_populates="stream_products")
    product = relationship("Product", back_populates="stream_products")


class StreamSessionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    avatar_path: str  # Accept avatar path from filesystem
    product_ids: List[int]


class StreamSessionResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    avatar_id: int
    avatar: AvatarResponse  # Include avatar details
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class StreamProductResponse(BaseModel):
    id: int
    product_id: int
    order_in_stream: int
    script_text: Optional[str]
    audio_path: Optional[str]
    video_path: Optional[str]
    duration_seconds: int
    is_processed: bool
    product: ProductResponse

    class Config:
        from_attributes = True

