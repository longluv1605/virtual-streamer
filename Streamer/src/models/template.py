from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
)

from pydantic import BaseModel

from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from .models import Base


class ScriptTemplate(Base):
    __tablename__ = "script_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    template = Column(Text, nullable=False)  # Template với placeholders
    category = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())



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
