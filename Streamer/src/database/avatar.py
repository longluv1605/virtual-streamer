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
    def get_or_create_avatar(
        db: Session, video_path: str, name: str = None, 
        compress: bool = False,
        compress_fps: int = None,
        compress_resolution: int = None,
        compress_bitrate: int = None
    ) -> Avatar:
        """Get existing avatar or create new one"""
        try:
            if not compress:
                if compress_fps or compress_resolution or compress_bitrate:
                    raise ValueError("Compress is none but its atribute are not!")
            elif not compress_fps or not compress_resolution or not compress_bitrate:
                raise ValueError("Compress is True but some compress attribute are missing!")
            
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

            avatar = Avatar(
                video_path=video_path,
                name=name,
                is_prepared=False,
                compress=compress,
                compress_fps=compress_fps,
                compress_resolution=compress_resolution,
                compress_bitrate=compress_bitrate
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
        db: Session, avatar_id: int, video_path: str = None, is_prepared: bool = None
    ):
        """Update avatar preparation status"""
        try:
            avatar = db.query(Avatar).filter(Avatar.id == avatar_id).first()
            if not avatar:
                raise ValueError(f"Avatar with ID {avatar_id} not found")

            if is_prepared is not None:
                avatar.is_prepared = is_prepared
            
            if video_path is not None:
                avatar.video_path = video_path

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
    def get_avatars(db: Session, skip: int = 0, limit: int = 100) -> List[Avatar]:
        """List all avatars"""
        return db.query(Avatar).offset(skip).limit(limit).all()

    @staticmethod
    def get_default_avatars(db: Session) -> List[Avatar]:
        """List all system avatars"""
        return db.query(Avatar).filter(Avatar.default == True)