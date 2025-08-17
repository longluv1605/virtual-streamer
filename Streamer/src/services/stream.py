import time
import numpy as np
import threading
from typing import Optional, List
from sqlalchemy.orm import Session

from src.models import ScriptTemplate, Avatar

from .llm import LLMService
from .tts import TTSService
from .musetalk import MuseTalkService, get_musetalk_realtime_service
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
        self.llm_service = LLMService()
        self.tts_service = TTSService()
        self.musetalk_service = MuseTalkService()

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
                    session.for_stream,
                    session.stream_fps,
                    session.batch_size,
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

    async def process_question_answer(
        self,
        session_id: int,
        comment_id: int,
        question: str,
        db_session,
        context: str = None,
    ) -> Optional[str]:
        """Process Q&A during live session - generate answer video using existing prepared avatar"""

        try:
            # Get session and avatar
            from src.database import (
                StreamSessionDatabaseService,
                CommentDatabaseService,
            )

            session = StreamSessionDatabaseService.get_session(db_session, session_id)
            if not session:
                logger.warning(f"Session {session_id} not found")
                return None

            avatar = session.avatar
            if not avatar:
                logger.warning(f"Avatar not found for session {session_id}")
                return None

            if not avatar.is_prepared:
                logger.warning(
                    f"Warning: Avatar {avatar.name} is not prepared, but proceeding..."
                )

            logger.info(
                f"Processing Q&A for session {session_id}, comment {comment_id}"
            )
            logger.info(f"Question: {question}")

            # Generate answer using LLM
            answer = await self._generate_answer(question, context, session)
            logger.info(f"Generated answer: {answer}")

            # Generate audio for answer
            audio_filename = f"answer_{session_id}_{comment_id}"
            audio_path = await self.tts_service.text_to_speech(answer, audio_filename)

            if not audio_path:
                logger.warning("Failed to generate audio for answer")
                return None

            # Generate video using existing prepared avatar
            video_filename = f"answer_{session_id}_{comment_id}"
            video_path = await self.musetalk_service.generate_video_with_avatar(
                audio_path, avatar, session_id, f"qa_{comment_id}", video_filename
            )

            if video_path:
                # Update comment with answer video path
                CommentDatabaseService.update_comment_answer_video(
                    db_session, comment_id, video_path
                )
                logger.info(f"Successfully generated answer video: {video_path}")
                return video_path
            else:
                logger.warning("Failed to generate answer video")
                return None

        except Exception as e:
            logger.error(
                f"Error processing Q&A for session {session_id}, comment {comment_id}: {e}"
            )
            return None

    async def _generate_answer(self, question: str, context: str, session) -> str:
        """Generate answer for a question using LLM"""

        # Create context-aware prompt
        prompt = f"""
Bạn là một người bán hàng livestream chuyên nghiệp, thân thiện và am hiểu sản phẩm. 
Hãy trả lời câu hỏi của khách hàng một cách tự nhiên, hữu ích và khuyến khích mua hàng.

Thông tin livestream:
- Tiêu đề: {session.title}
- Mô tả: {session.description or "Livestream bán hàng"}

Câu hỏi của khách hàng: {question}

{f"Bối cảnh thêm: {context}" if context else ""}

Yêu cầu trả lời:
1. Ngắn gọn, rõ ràng (10-15 giây khi đọc)
2. Thân thiện, nhiệt tình
3. Cung cấp thông tin hữu ích
4. Khuyến khích tương tác tiếp tục
5. Nếu có thể, gợi ý sản phẩm phù hợp

Hãy trả lời:
"""

        try:
            if self.llm_service.provider == "openai" and self.llm_service.openai_client:
                response = await self.llm_service.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "Bạn là chuyên gia livestream bán hàng thân thiện và chuyên nghiệp.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=200,
                    temperature=0.7,
                )

                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating answer with LLM: {e}")

        # Fallback answer
        return f"Cảm ơn bạn đã đặt câu hỏi! Đây là một câu hỏi rất hay. Chúng tôi sẽ hỗ trợ bạn tốt nhất có thể trong livestream này!"

    async def get_unanswered_questions(self, session_id: int, db_session) -> List[dict]:
        """Get all unanswered questions for a session"""
        try:
            from src.database import CommentDatabaseService

            questions = CommentDatabaseService.get_unanswered_questions(
                db_session, session_id
            )

            return [
                {
                    "id": q.id,
                    "username": q.username,
                    "message": q.message,
                    "timestamp": q.timestamp.isoformat(),
                    "session_id": q.session_id,
                }
                for q in questions
            ]

        except Exception as e:
            logger.error(
                f"Error getting unanswered questions for session {session_id}: {e}"
            )
            return []

    async def _process_stream_product(
        self,
        stream_product,
        template: ScriptTemplate,
        avatar: Avatar,
        session_id: int,
        for_stream: bool,
        stream_fps: int,
        batch_size: int,
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

            if not for_stream:
                # Generate video using avatar system
                logger.info(
                    f"Generating video for {product.name} with avatar {avatar.name}..."
                )
                video_filename = f"output_{session_id}_{product.id}"
                video_path = await self.musetalk_service.generate_video_with_avatar(
                    audio_path,
                    stream_fps,
                    batch_size,
                    avatar,
                    session_id,
                    product.id,
                    video_filename,
                )
                update_data["video_path"] = video_path

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

    def start_realtime_session(self, db: Session, session_id: str):
        """Start realtime stream session with MuseTalk integration."""
        try:
            # Tạo session và lấy queue
            webrtc_service.ensure_session(session_id)
            video_q = webrtc_service.get_producer_queues(session_id)
            logger.info(f"Realtime session {session_id} started...")
        except Exception as e:
            logger.error(f"Failed to start session {session_id}")
            return {"status": "error", "detail": str(e)}

        try:
            musetalk_service = get_musetalk_realtime_service()
            session = StreamSessionDatabaseService.get_session(db, session_id)
            avatar_id = session.avatar_id

            # Create avatar
            # if not session.avatar.is_prepared:
            result = self.prepare_avatar_for_realtime(musetalk_service, session)
            if not result:
                return {"status": "error", "detail": "cannot create avatar..."}

        except Exception as e:
            logger.error(f"Error create avatar: {e}")

        def _produce():
            try:
                # Check if we have MuseTalk ready
                if musetalk_service.is_ready() and avatar_id:
                    try:
                        logger.info(f"Using MuseTalk for session {session_id}")
                        # Use MuseTalk for real generation
                        session_products = (
                            StreamSessionDatabaseService.get_session_products(
                                db, session_id
                            )
                        )
                        fps = session.stream_fps
                        batch_size = session.batch_size
                        for product in session_products:
                            musetalk_service.generate_frames_for_webrtc(
                                audio_path=product.audio_path,
                                video_queue=video_q,
                                fps=fps,
                                batch_size=batch_size,
                            )
                            time.sleep(session.wait_duration)
                    except Exception as e:
                        logger.error(f"Error produce musetalk realtime ...: {e}")
                        raise e
                else:
                    logger.info(f"Fallback to demo mode for session {session_id}")
                    # Fallback to demo generation
                    idx = 0

                    while idx < fps * 60:  # Demo 60 giây
                        # Demo frame với text hiển thị thông tin
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)

                        # Create demo pattern
                        color_intensity = (idx * 3) % 255
                        frame[:, :, 0] = color_intensity  # Red channel cycling

                        # Add text overlay indicating demo mode
                        import cv2

                        cv2.putText(
                            frame,
                            f"DEMO MODE - Frame {idx}",
                            (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,
                            (255, 255, 255),
                            2,
                        )
                        cv2.putText(
                            frame,
                            f"FPS: {fps}",
                            (50, 100),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (255, 255, 255),
                            2,
                        )
                        if avatar_id:
                            cv2.putText(
                                frame,
                                f"Avatar: {avatar_id}",
                                (50, 150),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (255, 255, 255),
                                2,
                            )

                        # Demo audio với tone
                        # t = np.arange(chunk_len) / sample_rate
                        # audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

                        try:
                            video_q.put((idx, frame), timeout=0.1)
                            # audio_q.put((idx, audio), timeout=0.1)
                        except:
                            pass  # Queue full, drop frame

                        time.sleep(1 / fps)
                        idx += 1

            except Exception as e:
                print(f"Producer thread error in session {session_id}: {e}")

        threading.Thread(target=_produce, daemon=True).start()

        # Get audio URL from session products
        audio_url = None
        try:
            session_products = StreamSessionDatabaseService.get_session_products(
                db, session_id
            )
            if session_products and session_products[0].audio_path:
                # Convert relative path to web URL
                audio_path = session_products[0].audio_path
                # Normalize path separators and check if already starts with outputs
                normalized_path = audio_path.replace("\\", "/")
                if normalized_path.startswith("outputs/"):
                    audio_url = f"/{normalized_path}"
                else:
                    audio_url = f"/outputs/audio/{normalized_path}"
        except Exception as e:
            logger.warning(f"Could not get audio URL: {e}")

        return {
            "status": "realtime_started",
            "audio_url": audio_url,
            "fps": session.stream_fps,
        }

    def prepare_avatar_for_realtime(self, musetalk_service, session) -> bool:
        """
        Prepare avatar cho realtime streaming - gọi trước khi start session
        """
        try:
            # Get session avatar info
            avatar_id = session.avatar_id
            avatar_video_path = session.avatar.video_path
            avatar_preparation = not session.avatar.is_prepared
            fps = session.stream_fps
            batch_size = session.batch_size

            # Create avatar
            return musetalk_service.prepare_avatar(
                avatar_id, avatar_video_path, avatar_preparation, fps, batch_size
            )
        except Exception as e:
            logger.error(f"Error create avatar: {e}")
            return False


#######################################
stream_processor = StreamProcessor()
