from sqlalchemy.orm import Session
from src.models import Comment, CommentCreate
from typing import List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s")
logger = logging.getLogger(__name__)


class CommentDatabaseService:
    @staticmethod
    def create_comment(db: Session, session_id: int, comment: CommentCreate) -> Comment:
        try:
            logger.info(
                f"Creating comment for session {session_id}: {comment.username} - {comment.message[:50]}..."
            )
            db_comment = Comment(session_id=session_id, **comment.dict())
            db.add(db_comment)
            db.commit()
            db.refresh(db_comment)
            logger.info(f"Successfully created comment {db_comment.id}")
            return db_comment
        except Exception as e:
            logger.error(f"Error creating comment for session {session_id}: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_session_comments(
        db: Session, session_id: int, skip: int = 0, limit: int = 100
    ) -> List[Comment]:
        try:
            comments = (
                db.query(Comment)
                .filter(Comment.session_id == session_id)
                .order_by(Comment.timestamp.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            logger.info(f"Retrieved {len(comments)} comments for session {session_id}")
            return comments
        except Exception as e:
            logger.error(f"Error getting comments for session {session_id}: {e}")
            raise

    @staticmethod
    def get_unanswered_questions(db: Session, session_id: int) -> List[Comment]:
        try:
            questions = (
                db.query(Comment)
                .filter(
                    Comment.session_id == session_id,
                    Comment.is_question == True,
                    Comment.answered == False,
                )
                .order_by(Comment.timestamp)
                .all()
            )
            logger.info(
                f"Retrieved {len(questions)} unanswered questions for session {session_id}"
            )
            return questions
        except Exception as e:
            logger.error(f"Error getting unanswered questions for session {session_id}: {e}")
            raise

    @staticmethod
    def mark_comment_answered(db: Session, comment_id: int) -> Optional[Comment]:
        try:
            logger.info(f"Marking comment {comment_id} as answered")
            db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
            if db_comment:
                db_comment.answered = True
                db.commit()
                db.refresh(db_comment)
                logger.info(f"Successfully marked comment {comment_id} as answered")
            else:
                logger.warning(f"Comment {comment_id} not found")
            return db_comment
        except Exception as e:
            logger.error(f"Error marking comment {comment_id} as answered: {e}")
            db.rollback()
            raise

    @staticmethod
    def update_comment_answer_video(
        db: Session, comment_id: int, video_path: str
    ) -> Optional[Comment]:
        """Update comment with answer video path and mark as answered"""
        try:
            logger.info(f"Updating comment {comment_id} with answer video: {video_path}")
            db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
            if db_comment:
                db_comment.answered = True
                db_comment.answer_video_path = video_path
                db.commit()
                db.refresh(db_comment)
                logger.info(f"Successfully updated comment {comment_id} with answer video")
            else:
                logger.warning(f"Comment {comment_id} not found")
            return db_comment
        except Exception as e:
            logger.error(f"Error marking comment {comment_id} as answered: {e}")
            db.rollback()
            raise
