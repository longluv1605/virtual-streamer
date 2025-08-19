import time
import numpy as np
import threading
from pathlib import Path
from typing import Optional, List
from sqlalchemy.orm import Session

from src.models import ScriptTemplate, Avatar

from .llm import LLMService
from .tts import TTSService
from .musetalk import get_musetalk_realtime_service
from .webrtc import webrtc_service
from ..database import StreamSessionDatabaseService

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s",
)
logger = logging.getLogger(__name__)


class StreamProcessor:
    """Main service to process stream sessions"""

    def __init__(self):
        self.base_dir = Path('../Streamer')
        self.llm_service = LLMService()
        self.tts_service = TTSService(provider="gtts")
        
        # Track realtime generation status per session.
        # Key: session_id, Value: dict with keys 'is_generating' (bool) and 'product_id' (str or None)
        # This allows the API layer to report whether a product is currently being generated.
        self._realtime_status = {}

    async def process_session(self, session_id: int, db_session) -> bool:
        """Process entire stream session"""
        from src.database import (
            StreamSessionDatabaseService,
            ScriptTemplateDatabaseService,
        )

        try:
            # Get session and products
            session = StreamSessionDatabaseService.get_session(db_session, session_id)
            if not session:
                logger.warning(f"Session {session_id} not found")
                return False

            # Get avatar
            avatar = session.avatar
            if not avatar:
                logger.warning(f"Avatar not found for session {session_id}")
                return False

            stream_products = StreamSessionDatabaseService.get_session_products(
                db_session, session_id
            )
            if not stream_products:
                logger.warning(f"No products found for session {session_id}")
                return False

            # Get default template
            templates = ScriptTemplateDatabaseService.get_templates(db_session)
            default_template = templates[0] if templates else None

            if not default_template:
                logger.warning("No script template found")
                return False

            # Ensure avatar is prepared
            if not avatar.is_prepared:
                logger.warning(f"Avatar {avatar.name} is not prepared...")

            if not session.for_stream:
                logger.warning(f"Session is not realtime streaming...")

            logger.info(
                f"Prepare session with {session.stream_fps} FPS and size {session.batch_size}"
            )

            # Process each product
            for stream_product in stream_products:
                await self._process_stream_product(
                    stream_product,
                    default_template,
                    avatar,
                    session_id,
                    db_session,
                )

            # Update session status
            StreamSessionDatabaseService.update_session_status(
                db_session, session_id, "ready"
            )
            logger.info(f"Session {session_id} processed successfully")
            return True

        except Exception as e:
            logger.error(f"Error processing session {session_id}: {e}")
            StreamSessionDatabaseService.update_session_status(
                db_session, session_id, "error"
            )
            return False

    async def _process_stream_product(
        self,
        stream_product,
        template: ScriptTemplate,
        avatar: Avatar,
        session_id: int,
        db_session,
    ):
        """Process individual stream product"""
        from src.database import StreamSessionDatabaseService

        try:
            product = stream_product.product

            # Generate script
            logger.info(f"Generating script for {product.name}...")
            script = await self.llm_service.generate_product_script(product, template)

            # Generate audio
            logger.info(f"Generating audio for {product.name}...")
            audio_filename = f"product_{session_id}_{product.id}"
            audio_path = await self.tts_service.text_to_speech(script, audio_filename)

            # Update database
            update_data = {
                "script_text": script,
                "audio_path": audio_path,
                "is_processed": True,
            }

            StreamSessionDatabaseService.update_stream_product(
                db_session, stream_product.id, update_data
            )

            logger.info(
                f"Processed {product.name} successfully with avatar {avatar.name}"
            )

        except Exception as e:
            logger.error(f"Error processing stream product {stream_product.id}: {e}")
            # Mark as failed
            StreamSessionDatabaseService.update_stream_product(
                db_session, stream_product.id, {"is_processed": False}
            )


    def prepare_avatar_for_realtime(self, musetalk_service, session) -> bool:
        """
        Prepare avatar cho realtime streaming - gọi trước khi start session
        """
        try:
            # Get session avatar info
            avatar_id = session.avatar_id
            avatar_video_path = session.avatar.video_path
            avatar_preparation = not session.avatar.is_prepared

            # Create avatar
            return musetalk_service.prepare_avatar(
                avatar_id, avatar_video_path, avatar_preparation
            )
        except Exception as e:
            logger.error(f"Error create avatar: {e}")
            return False


    # === New realtime methods for per-product generation ===
    async def start_product(self, db: Session, session_id: str, product_id: str):
        """
        Start realtime generation for a single product. If a generation is already in progress for this
        session, an error is returned. The method returns the audio URL, fps and estimated duration
        for the requested product.

        Parameters
        ----------
        db : Session
            Database session for retrieving session and product info.
        session_id : str
            The session identifier.
        product_id : str
            The identifier of the product to generate frames for.

        Returns
        -------
        dict
            A dictionary containing the status of the operation and, on success, the audio URL
            and FPS for the product.
        """
        # Make sure session exists and product belongs to the session
        from src.database import StreamSessionDatabaseService
        try:
            logger.info("Starting product live generation...")
            session = StreamSessionDatabaseService.get_session(db, session_id)
            musetalk_service = get_musetalk_realtime_service()
            
            if not session:
                return {"status": "error", "detail": f"Session {session_id} not found"}
            if not musetalk_service:
                return {"status": "error", "detail": f"MuseTalk service is not available"} 
            
            try:           
                self.prepare_avatar_for_realtime(musetalk_service, session)
                logger.info("Session's avatar is ready...")
            except Exception as e:
                logger.error(f"Error preparing avatar for realtime: {e}")
                return {"status": "error", "detail": "Failed to prepare avatar"}

            # Check if there is an ongoing generation
            if self._realtime_status.get(session_id, {}).get("is_generating"):
                return {"status": "error", "detail": "Another product is currently generating"}

            # Retrieve the product within this session
            # We use product_id as string; convert to int for lookup
            try:
                pid_int = int(product_id)
            except Exception:
                pid_int = product_id
            products = StreamSessionDatabaseService.get_session_products(db, session_id)
            stream_product = None
            for sp in products:
                if str(sp.id) == str(pid_int) or str(sp.product_id) == str(pid_int):
                    stream_product = sp
                    break
            if not stream_product:
                return {"status": "error", "detail": f"Product {product_id} not found in session"}

            # Ensure audio is available for this product
            audio_path = stream_product.audio_path
            if not audio_path:
                return {"status": "error", "detail": "No audio available for this product"}

            # Get or create WebRTC session
            webrtc_service.ensure_session(session_id)
            video_q = webrtc_service.get_producer_queues(session_id)

            # Mark generation in progress
            self._realtime_status[session_id] = {
                "is_generating": True,
                "product_id": str(pid_int),
            }

            # Estimate duration for client (fallback to 30s)
            estimated_duration = 30
            try:
                import os
                import librosa

                abs_audio_path = os.path.join(self.base_dir, audio_path)
                if os.path.exists(abs_audio_path):
                    y, sr = librosa.load(abs_audio_path, sr=None)
                    estimated_duration = max(librosa.get_duration(y=y, sr=sr), 10)
            except Exception as e:
                logger.warning(f"Could not estimate audio duration for product {product_id}: {e}")

            # Convert audio path to URL
            normalized_path = audio_path.replace("\\", "/")
            audio_url = normalized_path if normalized_path.startswith("/") else f"/{normalized_path}"

            # Use session fps
            fps = session.stream_fps or 25
            batch_size = session.batch_size or 1

            # Start producer thread for this product only
            def _produce_single():
                try:
                    # Use musetalk realtime service
                    # musetalk_service = get_musetalk_realtime_service()
                    if musetalk_service.is_ready():
                        try:
                            musetalk_service.generate_frames_for_webrtc(
                                audio_path=audio_path,
                                video_queue=video_q,
                                fps=fps,
                                batch_size=batch_size,
                            )
                        except Exception as e:
                            logger.error(f"Error generating frames for product {product_id}: {e}")
                    else:
                        # Fallback: generate dummy frames
                        idx = 0
                        total_frames = int(fps * estimated_duration)
                        while idx < total_frames:
                            frame = np.zeros((480, 640, 3), dtype=np.uint8)
                            color_intensity = (idx * 3) % 255
                            frame[:, :, 0] = color_intensity
                            try:
                                video_q.put((idx, frame), timeout=0.1)
                            except:
                                pass
                            time.sleep(1 / fps)
                            idx += 1
                finally:
                    # Mark generation finished
                    self._realtime_status[session_id] = {
                        "is_generating": False,
                        "product_id": None,
                    }

            threading.Thread(target=_produce_single, daemon=True).start()

            return {
                "status": "started",
                "audio_url": audio_url,
                "fps": fps,
                "duration": estimated_duration,
            }
        except Exception as e:
            logger.error(f"Error starting product {product_id} for session {session_id}: {e}")
            # On error, clear status
            self._realtime_status[session_id] = {
                "is_generating": False,
                "product_id": None,
            }
            return {"status": "error", "detail": str(e)}

    def realtime_status(self, session_id: str) -> dict:
        """Return realtime generation status for a given session."""
        status = self._realtime_status.get(session_id)
        if not status:
            return {"exists": False}
        return {
            "exists": True,
            "is_generating": status.get("is_generating", False),
            "product_id": status.get("product_id"),
        }


#######################################
stream_processor = StreamProcessor()
