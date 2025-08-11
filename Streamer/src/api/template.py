from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from typing import List, Optional

from ..database import get_db, ScriptTemplateService
from ..models import (
    ScriptTemplateCreate,
    ScriptTemplateResponse,
)


####################################
router = APIRouter(prefix="/templates", tags=["templates"])

# Script template endpoints
@router.post("", response_model=ScriptTemplateResponse)
async def create_template(
    template: ScriptTemplateCreate, db: Session = Depends(get_db)
):
    return ScriptTemplateService.create_template(db, template)


@router.get("", response_model=List[ScriptTemplateResponse])
async def get_templates(category: Optional[str] = None, db: Session = Depends(get_db)):
    return ScriptTemplateService.get_templates(db, category)
