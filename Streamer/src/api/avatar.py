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
import asyncio

from ..database import get_db, AvatarDatabaseService
from ..models import (
    AvatarCreate,
    AvatarUpdate,
    AvatarResponse,
)

import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


####################################
router = APIRouter(prefix="/avatars", tags=["avatars"])


# Avatar endpoints
@router.get("")
async def get_available_avatars():
    """Get list of available avatar videos from both local and MuseTalk directories"""
    avatar_files = []
    video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    image_extensions = {".png", ".jpg", ".jpeg"}

    # 1. Check local avatars directory
    local_avatars_dir = Path("static/avatars")
    local_avatars_dir.mkdir(exist_ok=True)

    for file_path in local_avatars_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            avatar_files.append(
                {
                    "name": f"Local: {file_path.stem}",
                    "filename": file_path.name,
                    "path": f"/static/avatars/{file_path.name}",
                    "size": file_path.stat().st_size,
                    "source": "local",
                    "type": "video",
                }
            )

    # 2. Check MuseTalk video avatars directory
    musetalk_video_dir = Path("../MuseTalk/data/video")
    if musetalk_video_dir.exists():
        for file_path in musetalk_video_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                # Use relative path for easier handling
                relative_path = f"../MuseTalk/data/video/{file_path.name}"
                avatar_files.append(
                    {
                        "name": f"MuseTalk Video: {file_path.stem}",
                        "filename": file_path.name,
                        "path": relative_path,
                        "size": file_path.stat().st_size,
                        "source": "musetalk_video",
                        "type": "video",
                    }
                )

    # 3. Check MuseTalk demo images (can be used for image-based avatars)
    musetalk_demo_dir = Path("../MuseTalk/assets/demo")
    if musetalk_demo_dir.exists():
        for demo_folder in musetalk_demo_dir.iterdir():
            if demo_folder.is_dir():
                # Look for image files in each demo folder
                for file_path in demo_folder.iterdir():
                    if (
                        file_path.is_file()
                        and file_path.suffix.lower() in image_extensions
                    ):
                        # Use relative path for easier handling
                        relative_path = f"../MuseTalk/assets/demo/{demo_folder.name}/{file_path.name}"
                        avatar_files.append(
                            {
                                "name": f"MuseTalk Demo: {demo_folder.name}",
                                "filename": file_path.name,
                                "path": relative_path,
                                "size": file_path.stat().st_size,
                                "source": "musetalk_demo",
                                "type": "image",
                            }
                        )
                        break  # Only take one image per demo folder

    # Sort by source type and name
    avatar_files.sort(key=lambda x: (x["source"], x["name"]))

    return {"avatars": avatar_files}


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


# ===== AVATAR MANAGEMENT ENDPOINTS =====


@router.get("/database", response_model=List[AvatarResponse])
async def list_database_avatars(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """List all avatars in database"""
    try:
        avatars = AvatarDatabaseService.list_avatars(db, skip=skip, limit=limit)
        return avatars
    except Exception as e:
        logger.error(f"Error listing avatars: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database", response_model=AvatarResponse)
async def create_avatar(avatar_data: AvatarCreate, db: Session = Depends(get_db)):
    """Create or get existing avatar"""
    try:
        avatar = AvatarDatabaseService.get_or_create_avatar(
            db, video_path=avatar_data.video_path, name=avatar_data.name
        )
        # Update bbox_shift if provided
        if avatar_data.bbox_shift != 0:
            avatar.bbox_shift = avatar_data.bbox_shift
            db.commit()
            db.refresh(avatar)

        return avatar
    except Exception as e:
        logger.error(f"Error creating avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/{avatar_id}", response_model=AvatarResponse)
async def get_avatar(avatar_id: int, db: Session = Depends(get_db)):
    """Get avatar by ID"""
    avatar = AvatarDatabaseService.get_avatar_by_id(db, avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return avatar


@router.put("/database/{avatar_id}", response_model=AvatarResponse)
async def update_avatar(
    avatar_id: int, avatar_update: AvatarUpdate, db: Session = Depends(get_db)
):
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
        if avatar_update.is_prepared is not None:
            avatar.is_prepared = avatar_update.is_prepared

        db.commit()
        db.refresh(avatar)
        return avatar
    except Exception as e:
        logger.error(f"Error updating avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database/{avatar_id}/prepare")
async def prepare_avatar(
    avatar_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """Prepare avatar for MuseTalk"""
    try:
        avatar = AvatarDatabaseService.get_avatar_by_id(db, avatar_id)
        if not avatar:
            raise HTTPException(status_code=404, detail="Avatar not found")

        if avatar.is_prepared:
            return {"message": "Avatar already prepared", "avatar_id": avatar_id}

        # Start background preparation
        AvatarDatabaseService.update_avatar_preparation_status(db, avatar_id, "processing")

        # TODO: Add actual preparation logic here
        # For now, just mark as prepared
        background_tasks.add_task(_prepare_avatar_background, avatar_id)

        return {"message": "Avatar preparation started", "avatar_id": avatar_id}

    except Exception as e:
        logger.error(f"Error preparing avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _prepare_avatar_background(avatar_id: int):
    """Background task to prepare avatar"""
    try:
        # Get database session
        from src.models import SessionLocal

        db = SessionLocal()

        try:
            # Update status to processing
            AvatarDatabaseService.update_avatar_preparation_status(db, avatar_id, "processing")

            # TODO: Add actual MuseTalk preparation logic here
            # For now, just simulate preparation
            await asyncio.sleep(5)  # Simulate processing time

            # Mark as prepared
            AvatarDatabaseService.update_avatar_preparation_status(
                db, avatar_id, "completed", is_prepared=True
            )

            logger.info(f"Avatar {avatar_id} preparation completed")

        finally:
            db.close()

    except Exception as e:
        logger.info(f"Error in background avatar preparation: {e}")
        # Mark as error if failed
        try:
            from src.models import SessionLocal

            db = SessionLocal()
            AvatarDatabaseService.update_avatar_preparation_status(db, avatar_id, "error")
            db.close()
        except:
            pass

