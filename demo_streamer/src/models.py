from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Optional
import json

Base = declarative_base()


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


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    image_url = Column(String(500))
    category = Column(String(100))
    stock_quantity = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship
    stream_products = relationship("StreamProduct", back_populates="product")


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


class ScriptTemplate(Base):
    __tablename__ = "script_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    template = Column(Text, nullable=False)  # Template với placeholders
    category = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


# Database setup
DATABASE_URL = "sqlite:///./virtual_streamer.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic models for API
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    category: Optional[str] = None
    stock_quantity: int = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    stock_quantity: Optional[int] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    image_url: Optional[str]
    category: Optional[str]
    stock_quantity: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BulkProductUpdate(BaseModel):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    stock_quantity: Optional[int] = None


class ProductStatsResponse(BaseModel):
    total_products: int
    total_inactive: int
    categories: dict
    price_stats: dict
    stock_stats: dict


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


class ScriptTemplateCreate(BaseModel):
    name: str
    template: str
    category: Optional[str] = None


class ScriptTemplateResponse(BaseModel):
    id: int
    name: str
    template: str
    category: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Pagination models
class PaginatedProductResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    pages: int
    limit: int
