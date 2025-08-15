from sqlalchemy.orm import Session
from src.models import StreamSession, StreamSessionCreate, StreamProduct
from typing import List, Optional
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class StreamSessionDatabaseService:
    @staticmethod
    def create_session(db: Session, session_data: StreamSessionCreate) -> StreamSession:
        try:
            logger.info(
                f"Creating session: {session_data.title} with {len(session_data.product_ids)} products"
            )
            logger.info(f"Using avatar_path: {session_data.avatar_path}")

            # Get or create avatar from path
            from .avatar import AvatarDatabaseService

            avatar = AvatarDatabaseService.get_or_create_avatar(db, session_data.avatar_path)
            logger.info(f"Avatar resolved: {avatar.name} (ID: {avatar.id})")

            # Create stream session
            db_session = StreamSession(
                title=session_data.title,
                description=session_data.description,
                avatar_id=avatar.id,
                status="preparing",
                # Add streaming settings
                for_stream=session_data.for_stream,
                wait_duration=session_data.wait_duration,
                stream_fps=session_data.fps,
                batch_size=session_data.batch_size,
            )
            db.add(db_session)
            db.commit()
            db.refresh(db_session)

            # Add products to session
            for i, product_id in enumerate(session_data.product_ids):
                stream_product = StreamProduct(
                    session_id=db_session.id,
                    product_id=product_id,
                    order_in_stream=i + 1,
                )
                db.add(stream_product)

            db.commit()
            logger.info(
                f"Successfully created session {db_session.id}: {db_session.title} with avatar {avatar.name}"
            )
            return db_session
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_sessions(
        db: Session, skip: int = 0, limit: int = 100
    ) -> List[StreamSession]:
        try:
            sessions = db.query(StreamSession).offset(skip).limit(limit).all()
            logger.info(f"Retrieved {len(sessions)} sessions")
            return sessions
        except Exception as e:
            logger.error(f"Error getting sessions: {e}")
            raise

    @staticmethod
    def get_session(db: Session, session_id: int) -> Optional[StreamSession]:
        try:
            session = (
                db.query(StreamSession).filter(StreamSession.id == session_id).first()
            )
            logger.info(
                f"Retrieved session {session_id}: {'Found' if session else 'Not found'}"
            )
            return session
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise

    @staticmethod
    def get_session_products(db: Session, session_id: int) -> List[StreamProduct]:
        try:
            products = (
                db.query(StreamProduct)
                .filter(StreamProduct.session_id == session_id)
                .order_by(StreamProduct.order_in_stream)
                .all()
            )
            logger.info(f"Retrieved {len(products)} products for session {session_id}")
            return products
        except Exception as e:
            logger.error(f"Error getting session products for session {session_id}: {e}")
            raise

    @staticmethod
    def update_session_status(
        db: Session, session_id: int, status: str
    ) -> Optional[StreamSession]:
        try:
            db_session = (
                db.query(StreamSession).filter(StreamSession.id == session_id).first()
            )
            if db_session:
                logger.info(
                    f"Updating session {session_id} status from {db_session.status} to {status}"
                )
                db_session.status = status
                db.commit()
                db.refresh(db_session)
                logger.info(f"Successfully updated session {session_id} status to {status}")
            else:
                logger.warning(f"Session {session_id} not found for status update")
            return db_session
        except Exception as e:
            logger.error(f"Error updating session {session_id} status: {e}")
            db.rollback()
            raise

    @staticmethod
    def update_stream_product(
        db: Session, stream_product_id: int, update_data: dict
    ) -> Optional[StreamProduct]:
        try:
            logger.info(
                f"Updating stream product {stream_product_id} with data: {update_data}"
            )
            db_stream_product = (
                db.query(StreamProduct)
                .filter(StreamProduct.id == stream_product_id)
                .first()
            )
            if db_stream_product:
                for key, value in update_data.items():
                    setattr(db_stream_product, key, value)
                db.commit()
                db.refresh(db_stream_product)
                logger.info(f"Successfully updated stream product {stream_product_id}")
            else:
                logger.warning(f"Stream product {stream_product_id} not found")
            return db_stream_product
        except Exception as e:
            logger.error(f"Error updating stream product {stream_product_id}: {e}")
            db.rollback()
            raise
