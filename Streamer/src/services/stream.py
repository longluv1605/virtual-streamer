from typing import Optional, List
import threading
import time
import numpy as np

from src.models import ScriptTemplate, Avatar

from .llm import LLMService
from .tts import TTSService
from .musetalk import MuseTalkService
from .webrtc import webrtc_service


class StreamProcessor:
    """Main service to process stream sessions"""

    def __init__(self):
        self.llm_service = LLMService()
        self.tts_service = TTSService()
        self.musetalk_service = MuseTalkService()

    async def process_session(self, session_id: int, db_session) -> bool:
        """Process entire stream session"""
        from src.database import StreamSessionService, ScriptTemplateService

        try:
            # Get session and products
            session = StreamSessionService.get_session(db_session, session_id)
            if not session:
                print(f"Session {session_id} not found")
                return False

            # Get avatar
            avatar = session.avatar
            if not avatar:
                print(f"Avatar not found for session {session_id}")
                return False

            stream_products = StreamSessionService.get_session_products(
                db_session, session_id
            )
            if not stream_products:
                print(f"No products found for session {session_id}")
                return False

            # Get default template
            templates = ScriptTemplateService.get_templates(db_session)
            default_template = templates[0] if templates else None

            if not default_template:
                print("No script template found")
                return False

            # Ensure avatar is prepared
            if not avatar.is_prepared:
                print(f"Avatar {avatar.name} is not prepared...")

            if not session.for_stream:
                print(f"Session is not realtime streaming...")

            print(
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
            StreamSessionService.update_session_status(db_session, session_id, "ready")
            print(f"Session {session_id} processed successfully")
            return True

        except Exception as e:
            print(f"Error processing session {session_id}: {e}")
            StreamSessionService.update_session_status(db_session, session_id, "error")
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
            from src.database import StreamSessionService, CommentService

            session = StreamSessionService.get_session(db_session, session_id)
            if not session:
                print(f"Session {session_id} not found")
                return None

            avatar = session.avatar
            if not avatar:
                print(f"Avatar not found for session {session_id}")
                return None

            if not avatar.is_prepared:
                print(
                    f"Warning: Avatar {avatar.name} is not prepared, but proceeding..."
                )

            print(f"Processing Q&A for session {session_id}, comment {comment_id}")
            print(f"Question: {question}")

            # Generate answer using LLM
            answer = await self._generate_answer(question, context, session)
            print(f"Generated answer: {answer}")

            # Generate audio for answer
            audio_filename = f"answer_{session_id}_{comment_id}"
            audio_path = await self.tts_service.text_to_speech(answer, audio_filename)

            if not audio_path:
                print("Failed to generate audio for answer")
                return None

            # Generate video using existing prepared avatar
            video_filename = f"answer_{session_id}_{comment_id}"
            video_path = await self.musetalk_service.generate_video_with_avatar(
                audio_path, avatar, session_id, f"qa_{comment_id}", video_filename
            )

            if video_path:
                # Update comment with answer video path
                CommentService.update_comment_answer_video(
                    db_session, comment_id, video_path
                )
                print(f"Successfully generated answer video: {video_path}")
                return video_path
            else:
                print("Failed to generate answer video")
                return None

        except Exception as e:
            print(
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
            print(f"Error generating answer with LLM: {e}")

        # Fallback answer
        return f"Cảm ơn bạn đã đặt câu hỏi! Đây là một câu hỏi rất hay. Chúng tôi sẽ hỗ trợ bạn tốt nhất có thể trong livestream này!"

    async def get_unanswered_questions(self, session_id: int, db_session) -> List[dict]:
        """Get all unanswered questions for a session"""
        try:
            from src.database import CommentService

            questions = CommentService.get_unanswered_questions(db_session, session_id)

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
            print(f"Error getting unanswered questions for session {session_id}: {e}")
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
        from src.database import StreamSessionService

        try:
            product = stream_product.product

            # Generate script
            print(f"Generating script for {product.name}...")
            script = await self.llm_service.generate_product_script(product, template)

            # Generate audio
            print(f"Generating audio for {product.name}...")
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
                print(
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

            StreamSessionService.update_stream_product(
                db_session, stream_product.id, update_data
            )

            print(f"Processed {product.name} successfully with avatar {avatar.name}")

        except Exception as e:
            print(f"Error processing stream product {stream_product.id}: {e}")
            # Mark as failed
            StreamSessionService.update_stream_product(
                db_session, stream_product.id, {"is_processed": False}
            )

    def start_realtime_session(
        self, session_id: str, fps: int = 25, sample_rate: int = 16000
    ):
        """Start realtime stream session."""
        try:
            # Tạo session và lấy queue
            webrtc_service.ensure_session(session_id, fps=fps, sample_rate=sample_rate)
            video_q, audio_q = webrtc_service.get_producer_queues(session_id)
            print(
                f"Realtime session {session_id} started (fps={fps}, sr={sample_rate})"
            )
        except Exception as e:
            print(f"Failed to start session {session_id}")
            return {"status": "error", "detail": str(e)}

        def _produce():
            try:
                # TODO: Thay bằng tích hợp MuseTalk thật
                # Option 1: Import và sử dụng realtime_inference_synced.py
                # Option 2: Gọi subprocess
                # Option 3: Tích hợp trực tiếp MuseTalk models

                # Demo code - thay bằng MuseTalk thật:
                idx = 0
                chunk_len = int(sample_rate / fps)

                while idx < fps * 60:  # Demo 60 giây
                    # TODO: Lấy frame từ MuseTalk inference
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    frame[:] = (idx * 3) % 255

                    # TODO: Lấy audio chunk từ MuseTalk
                    t = np.arange(chunk_len) / sample_rate
                    audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

                    try:
                        video_q.put((idx, frame), timeout=0.1)
                        audio_q.put((idx, audio), timeout=0.1)
                    except:
                        pass  # Queue full, drop frame

                    time.sleep(1 / fps)
                    idx += 1

            except Exception as e:
                print(f"Producer thread error in session {session_id}: {e}")

        threading.Thread(target=_produce, daemon=True).start()
        return {"status": "realtime_started"}


#######################################
stream_processor = StreamProcessor()
