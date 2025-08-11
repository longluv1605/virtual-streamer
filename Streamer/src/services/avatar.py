from sqlalchemy.orm import Session
from src.models import Avatar
import os
from typing import List

class AvatarService:
    """Service for managing avatars and their preparation status"""

    @staticmethod
    def get_or_create_avatar(db: Session, video_path: str, name: str = None) -> Avatar:
        """Get existing avatar or create new one"""
        try:
            # Try to find existing avatar
            avatar = db.query(Avatar).filter(Avatar.video_path == video_path).first()

            if avatar:
                print(f"Found existing avatar: {avatar.name} (ID: {avatar.id})")
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
                preparation_status="pending",
                file_size=file_size,
            )

            db.add(avatar)
            db.commit()
            db.refresh(avatar)

            print(f"Created new avatar: {avatar.name} (ID: {avatar.id})")
            return avatar

        except Exception as e:
            print(f"Error in get_or_create_avatar: {e}")
            db.rollback()
            raise

    @staticmethod
    def update_avatar_preparation_status(
        db: Session, avatar_id: int, status: str, is_prepared: bool = None
    ):
        """Update avatar preparation status"""
        try:
            avatar = db.query(Avatar).filter(Avatar.id == avatar_id).first()
            if not avatar:
                raise ValueError(f"Avatar with ID {avatar_id} not found")

            avatar.preparation_status = status
            if is_prepared is not None:
                avatar.is_prepared = is_prepared

            db.commit()
            print(f"Updated avatar {avatar_id} status to: {status}")

        except Exception as e:
            print(f"Error updating avatar status: {e}")
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
