from sqlalchemy.orm import Session
from src.models import Avatar
import os
from typing import List

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s")
logger = logging.getLogger(__name__)

class AvatarDatabaseService:
    """Service for managing avatars and their preparation status"""

    @staticmethod
    def get_or_create_avatar(db: Session, video_path: str, name: str = None) -> Avatar:
        """Get existing avatar or create new one"""
        try:
            # Try to find existing avatar
            avatar = db.query(Avatar).filter(Avatar.video_path == video_path).first()

            if avatar:
                logger.info(f"Found existing avatar: {avatar.name} (ID: {avatar.id})")
                return avatar

            # Create new avatar
            if not name:
                # Generate name from path
                name = os.path.basename(video_path)
                if name.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                    name = name.rsplit(".", 1)[0]

            # Get file info if possible
            file_size = None
            if os.path.exists(video_path):
                file_size = os.path.getsize(video_path)

            avatar = Avatar(
                video_path=video_path,
                name=name,
                is_prepared=False,
                file_size=file_size,
            )

            db.add(avatar)
            db.commit()
            db.refresh(avatar)

            logger.info(f"Created new avatar: {avatar.name} (ID: {avatar.id})")
            return avatar

        except Exception as e:
            logger.error(f"Error in get_or_create_avatar: {e}")
            db.rollback()
            raise

    @staticmethod
    def update_avatar_preparation_status(
        db: Session, avatar_id: int, is_prepared: bool = None
    ):
        """Update avatar preparation status"""
        try:
            avatar = db.query(Avatar).filter(Avatar.id == avatar_id).first()
            if not avatar:
                raise ValueError(f"Avatar with ID {avatar_id} not found")

            if is_prepared is not None:
                avatar.is_prepared = is_prepared

            db.commit()
            logger.info(f"Updated avatar {avatar_id} preparation to: {is_prepared}")

        except Exception as e:
            logger.error(f"Error updating avatar status: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_avatar_by_id(db: Session, avatar_id: int) -> Avatar:
        """Get avatar by ID"""
        return db.query(Avatar).filter(Avatar.id == avatar_id).first()

    @staticmethod
    def list_avatars(db: Session, skip: int = 0, limit: int = 100) -> List[Avatar]:
        """List all avatars"""
        return db.query(Avatar).offset(skip).limit(limit).all()
