from sqlalchemy.orm import Session
from fastapi import (
    APIRouter, 
    Depends, 
    BackgroundTasks, 
    HTTPException,
    UploadFile,
    File
)
from typing import List
from pathlib import Path
import gc

from ..database import get_db, AvatarDatabaseService
from ..models import (
    AvatarCreate,
    AvatarUpdate,
    AvatarResponse,
)

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s")
logger = logging.getLogger(__name__)


####################################
router = APIRouter(prefix="/avatars", tags=["avatars"])

@router.post("/upload")
async def upload_avatar(file: UploadFile = File(...)):
    """Upload avatar video file"""
    # Validate file type
    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".webm")):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only video files are allowed."
        )

    # Create avatars directory if it doesn't exist
    avatars_dir = Path("static/avatars")
    avatars_dir.mkdir(exist_ok=True)

    # Save file
    file_path = avatars_dir / file.filename
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return {
        "message": "Avatar uploaded successfully",
        "filename": file.filename,
        "path": f"/static/avatars/{file.filename}",
    }


# ===== AVATAR ENDPOINTS =====
@router.get("", response_model=List[AvatarResponse])
async def get_avatars(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """List all avatars in database"""
    try:
        avatars = AvatarDatabaseService.get_avatars(db, skip=skip, limit=limit)
        return avatars
    except Exception as e:
        logger.error(f"Error listing avatars: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{avatar_id}", response_model=AvatarResponse)
async def get_avatar_by_id(avatar_id: int, db: Session = Depends(get_db)):
    """Get avatar by ID"""
    avatar = AvatarDatabaseService.get_avatar_by_id(db, avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return avatar


@router.post("", response_model=AvatarResponse)
async def create_avatar(avatar_data: AvatarCreate, db: Session = Depends(get_db)):
    """Create or get existing avatar"""
    try:
        avatar = AvatarDatabaseService.get_or_create_avatar(
            db, video_path=avatar_data.video_path, name=avatar_data.name
        )
        
        
        from src.services.musetalk import get_musetalk_realtime_service

        musetalk = get_musetalk_realtime_service()
        
        if not avatar.is_prepared:
            avatar_id = avatar.id
            video_path = avatar.video_path
            preparation = not avatar.is_prepared
            musetalk.prepare_avatar(avatar_id, video_path, preparation)
            
            musetalk._avatars.clear()
            del musetalk._current_avatar
            del musetalk; gc.collect()

        return avatar
    except Exception as e:
        logger.error(f"Error creating avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{avatar_id}", response_model=AvatarResponse)
async def update_avatar(avatar_id: int, avatar_update: AvatarUpdate, db: Session = Depends(get_db)):
    """Update avatar"""
    try:
        avatar = AvatarDatabaseService.get_avatar_by_id(db, avatar_id)
        if not avatar:
            raise HTTPException(status_code=404, detail="Avatar not found")

        # Update fields
        if avatar_update.name:
            avatar.name = avatar_update.name
        if avatar_update.bbox_shift is not None:
            avatar.bbox_shift = avatar_update.bbox_shift

        db.commit()
        db.refresh(avatar)
        return avatar
    except Exception as e:
        logger.error(f"Error updating avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# @router.delete("/{avatar_id}", response_model=AvatarResponse)
# async def update_avatar(avatar_id: int, db: Session = Depends(get_db)):
    """Delete avatar"""
    try:
        avatar = AvatarDatabaseService.get_avatar_by_id(db, avatar_id)
        if not avatar:
            raise HTTPException(status_code=404, detail="Avatar not found")

        # Update fields
        if avatar_update.name:
            avatar.name = avatar_update.name
        if avatar_update.bbox_shift is not None:
            avatar.bbox_shift = avatar_update.bbox_shift
        if avatar_update.is_prepared is not None:
            avatar.is_prepared = avatar_update.is_prepared

        db.commit()
        db.refresh(avatar)
        return avatar
    except Exception as e:
        logger.error(f"Error updating avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))