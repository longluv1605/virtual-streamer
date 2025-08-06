import openai
from openai import AsyncOpenAI
import os
from typing import Optional, List
from pathlib import Path
import asyncio
import aiohttp
from sqlalchemy.orm import Session
from src.models import Product, ScriptTemplate, Avatar, StreamSession
from dotenv import load_dotenv

load_dotenv()


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


class LLMService:
    """Service for LLM integration (OpenAI/Gemini)"""

    def __init__(self, provider: str = "openai", api_key: Optional[str] = None):
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv(
            "OPENAI_API_KEY" if provider == "openai" else "GEMINI_API_KEY"
        )

        if self.provider == "openai":
            if self.api_key:
                # Initialize OpenAI client following best practices
                self.openai_client = AsyncOpenAI(
                    api_key=self.api_key,
                    timeout=30.0,  # 30 second timeout
                    max_retries=2,  # Retry failed requests twice
                )
            else:
                self.openai_client = None
                print(
                    "Warning: OpenAI API key not found. LLM features will use fallback scripts."
                )
                print("To use OpenAI, set the OPENAI_API_KEY environment variable.")
        else:
            self.openai_client = None

    async def generate_product_script(
        self,
        product: Product,
        template: ScriptTemplate,
        additional_context: Optional[str] = None,
    ) -> str:
        """Generate product presentation script using LLM"""

        # Prepare prompt
        prompt = self._create_prompt(product, template, additional_context)

        try:
            if self.provider == "openai":
                return await self._generate_openai(prompt)
            elif self.provider == "gemini":
                return await self._generate_gemini(prompt)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
        except Exception as e:
            print(f"Error generating script: {e}")
            return self._fallback_script(product, template)

    def _create_prompt(
        self, product: Product, template: ScriptTemplate, additional_context: str
    ) -> str:
        """Create prompt for LLM"""

        context = f"""
Bạn là một người bán hàng livestream chuyên nghiệp, nhiệt tình và có kinh nghiệm. 
Hãy tạo một đoạn script để giới thiệu sản phẩm một cách hấp dẫn, thuyết phục và tự nhiên.

Thông tin sản phẩm:
- Tên: {product.name}
- Mô tả: {product.description or "Không có mô tả"}
- Giá: {product.price:,.0f} VNĐ
- Danh mục: {product.category or "Không xác định"}
- Số lượng trong kho: {product.stock_quantity}

Template cơ bản:
{template.template}

Yêu cầu:
1. Script phải tự nhiên, không quá dài (khoảng 10-20 giây khi đọc)
2. Sử dụng ngôn ngữ thân thiện, gần gũi
3. Tạo cảm giác khan hiếm và khẩn cấp phù hợp
4. Khuyến khích tương tác từ khán giả
5. Kết thúc bằng call-to-action rõ ràng

{f"Bối cảnh thêm: {additional_context}" if additional_context else ""}

Hãy tạo script hoàn chỉnh dựa trên template và thông tin trên:
"""
        return context

    async def _generate_openai(self, prompt: str) -> str:
        """Generate using OpenAI API"""
        if not self.openai_client:
            raise Exception(
                "OpenAI client not initialized. Please set OPENAI_API_KEY environment variable."
            )

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là chuyên gia viết script livestream bán hàng chuyên nghiệp. Hãy tạo script hấp dẫn, tự nhiên và thuyết phục.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
                temperature=0.7,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )

            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    return content.strip()
                else:
                    raise Exception("Empty response from OpenAI")
            else:
                raise Exception("No choices returned from OpenAI")

        except openai.RateLimitError as e:
            print(f"OpenAI Rate limit exceeded: {e}")
            raise Exception("Rate limit exceeded. Please try again later.")
        except openai.APIConnectionError as e:
            print(f"OpenAI API connection error: {e}")
            raise Exception("Failed to connect to OpenAI API.")
        except openai.AuthenticationError as e:
            print(f"OpenAI Authentication error: {e}")
            raise Exception("Invalid OpenAI API key.")
        except Exception as e:
            print(f"OpenAI API error: {e}")
            raise

    async def _generate_gemini(self, prompt: str) -> str:
        """Generate using Gemini API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                else:
                    raise Exception(f"Gemini API error: {response.status}")

    def _fallback_script(self, product: Product, template: ScriptTemplate) -> str:
        """Fallback script if LLM fails"""

        script = template.template.format(
            product_name=product.name,
            product_description=product.description or "Sản phẩm chất lượng cao",
            price=f"{product.price:,.0f}",
            stock_quantity=product.stock_quantity,
            features="Chất lượng cao, thiết kế đẹp, giá cả hợp lý",
            benefit_1="Tiết kiệm thời gian",
            benefit_2="Chất lượng đảm bảo",
            benefit_3="Giá cả cạnh tranh",
            detailed_description=product.description
            or "Sản phẩm được thiết kế với công nghệ hiện đại",
            comparison="Tính năng vượt trội và giá cả hợp lý hơn",
        )

        return script


class TTSService:
    """Text-to-Speech service"""

    def __init__(self, provider: str = "edge-tts"):
        self.provider = provider
        self.output_dir = Path("./outputs/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def text_to_speech(
        self, text: str, filename: str, voice: str = "vi-VN-HoaiMyNeural"
    ) -> str:
        """Convert text to speech and save as audio file"""

        output_path = self.output_dir / f"{filename}.mp3"

        try:
            if self.provider == "edge-tts":
                return await self._edge_tts(text, str(output_path), voice)
            else:
                raise ValueError(f"Unsupported TTS provider: {self.provider}")
        except Exception as e:
            print(f"Error in TTS: {e}")
            return None

    async def _edge_tts(self, text: str, output_path: str, voice: str) -> str:
        """Use Edge TTS (free Microsoft TTS)"""
        try:
            import edge_tts

            tts = edge_tts.Communicate(text, voice)
            await tts.save(output_path)
            return output_path
        except ImportError:
            print("edge-tts not installed. Installing...")
            import subprocess

            subprocess.check_call(["pip", "install", "edge-tts"])

            import edge_tts

            tts = edge_tts.Communicate(text, voice)
            await tts.save(output_path)
            return output_path
        except Exception as e:
            print(f"Edge TTS error: {e}")
            return None


class MuseTalkService:
    """MuseTalk integration service"""

    def __init__(self, musetalk_path: str = "../MuseTalk"):
        self.musetalk_path = Path(musetalk_path)
        self.output_dir = Path("./outputs/videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Validate MuseTalk installation
        self._validate_musetalk_setup()

    def _validate_musetalk_setup(self):
        """Validate MuseTalk installation and required files"""
        musetalk_abs_path = os.path.abspath(str(self.musetalk_path))

        required_files = [
            "scripts/realtime_inference.py",
            "models/musetalkV15/musetalk.json",
            "models/musetalkV15/unet.pth",
            "models/whisper",
            "musetalk/utils/dwpose",
        ]

        missing_files = []
        for file_path in required_files:
            full_path = os.path.join(musetalk_abs_path, file_path)
            if not os.path.exists(full_path):
                missing_files.append(file_path)

        if missing_files:
            print(f"Warning: MuseTalk setup incomplete. Missing files/directories:")
            for missing in missing_files:
                print(f"  - {missing}")
            print(
                f"Please ensure MuseTalk is properly installed at: {musetalk_abs_path}"
            )
        else:
            print(f"MuseTalk setup validated at: {musetalk_abs_path}")

    async def generate_video_with_avatar(
        self,
        audio_path: str,
        avatar: Avatar,
        session_id: int,
        product_id: int,
        output_filename: str,
    ) -> str:
        """Generate lip-sync video using avatar and audio for specific session/product"""

        output_path = self.output_dir / f"{output_filename}.mp4"

        try:
            # Import MuseTalk modules with proper path setup
            import sys
            import os

            # Store original working directory
            original_cwd = os.getcwd()

            # Get absolute path to MuseTalk
            musetalk_abs_path = os.path.abspath(str(self.musetalk_path))

            # Change to MuseTalk directory (important for relative imports)
            os.chdir(musetalk_abs_path)

            # Add MuseTalk to Python path
            if musetalk_abs_path not in sys.path:
                sys.path.insert(0, musetalk_abs_path)

            try:
                import subprocess
                import tempfile
                import yaml
                import sys

                # Convert paths to absolute paths
                print(f"Processing avatar: {avatar.name} (ID: {avatar.id})")
                print(f"Avatar path: {avatar.video_path}")
                print(f"Original working directory: {original_cwd}")

                # Fix audio path
                if not os.path.isabs(audio_path):
                    audio_abs_path = os.path.join(original_cwd, audio_path)
                else:
                    audio_abs_path = audio_path

                # Fix avatar path
                avatar_video_path = avatar.video_path
                if avatar_video_path.startswith("/static/"):
                    avatar_abs_path = os.path.join(
                        original_cwd, avatar_video_path.lstrip("/")
                    )
                elif avatar_video_path.startswith("../MuseTalk/"):
                    avatar_abs_path = os.path.abspath(avatar_video_path)
                elif os.path.isabs(avatar_video_path):
                    avatar_abs_path = avatar_video_path
                else:
                    avatar_abs_path = os.path.join(original_cwd, avatar_video_path)

                # Verify files exist
                if not os.path.exists(audio_abs_path):
                    raise FileNotFoundError(f"Audio file not found: {audio_abs_path}")
                if not os.path.exists(avatar_abs_path):
                    raise FileNotFoundError(
                        f"Avatar video not found: {avatar_abs_path}"
                    )

                # Verify MuseTalk model files exist
                required_models = [
                    "models/musetalk/pytorch_model.bin",
                    "models/dwpose/dw-ll_ucoco_384.pth",
                    "models/sd-vae/diffusion_pytorch_model.bin",
                ]

                missing_models = []
                for model_path in required_models:
                    full_model_path = os.path.join(musetalk_abs_path, model_path)
                    if not os.path.exists(full_model_path):
                        missing_models.append(model_path)

                if missing_models:
                    raise FileNotFoundError(
                        f"Required MuseTalk model files missing: {missing_models}. "
                        f"Please run the download script to get model files."
                    )

                print(f"Audio: {audio_abs_path}")
                print(f"Avatar: {avatar_abs_path}")
                print(f"MuseTalk models verified")

                # Create avatar ID based on avatar database ID (consistent across sessions)
                avatar_id = f"avatar_{avatar.id}"

                # Create audio clip key based on session and product
                audio_clip_key = f"{session_id}_{product_id}"

                # Create temporary config for realtime inference
                # Key insight: avatar_id stays same, but audio_clips has unique keys
                config_data = {
                    avatar_id: {
                        "preparation": not avatar.is_prepared,  # Only prepare if not already done
                        "video_path": avatar_abs_path,
                        "bbox_shift": avatar.bbox_shift,
                        "audio_clips": {
                            audio_clip_key: audio_abs_path
                        },  # Unique key per session/product
                    }
                }

                # Create temp config file
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".yaml", delete=False
                ) as f:
                    yaml.dump(config_data, f)
                    config_path = f.name

                print(f"Created config file: {config_path}")
                print(f"Config content:")
                print(yaml.dump(config_data, default_flow_style=False))
                print(f"Avatar preparation needed: {not avatar.is_prepared}")

                try:
                    # Run realtime inference via subprocess
                    print(f"Running realtime inference for avatar: {avatar_id}")
                    print(f"Audio clip key: {audio_clip_key}")

                    cmd = [
                        sys.executable,
                        "scripts/realtime_inference.py",
                        "--version",
                        "v15",
                        "--inference_config",
                        config_path,
                        "--batch_size",
                        "4",
                        "--fps",
                        "25",
                    ]

                    print(f"Command: {' '.join(cmd)}")

                    # Set environment for subprocess
                    env = os.environ.copy()
                    env["PYTHONPATH"] = musetalk_abs_path
                    env["PYTHONIOENCODING"] = "utf-8"  # Fix Unicode encoding issues

                    # Add CUDA settings for better memory management
                    env["CUDA_VISIBLE_DEVICES"] = "0"  # Use first GPU
                    env["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"

                    print("Starting MuseTalk inference process...")
                    try:
                        result = subprocess.run(
                            cmd,
                            cwd=musetalk_abs_path,
                            # capture_output=True,  # Capture output for better error handling
                            text=True,
                            # timeout=300,  # 5 minute timeout
                            env=env,  # Pass environment with PYTHONPATH
                            encoding="utf-8",  # Explicit UTF-8 encoding
                            errors="replace",  # Replace problematic characters
                        )
                    except subprocess.TimeoutExpired:
                        raise Exception(
                            "MuseTalk inference process timed out after 5 minutes"
                        )
                    except Exception as e:
                        raise Exception(
                            f"Failed to start MuseTalk inference process: {e}"
                        )

                    print(
                        "=================================================================="
                    )

                    if result.returncode != 0:
                        print(f"Realtime inference failed:")
                        print(f"STDOUT: {result.stdout}")
                        print(f"STDERR: {result.stderr}")
                        raise Exception(
                            f"Realtime inference process failed with code {result.returncode}"
                        )

                    print("Realtime inference completed successfully")
                    print(f"Output: {result.stdout}")
                    avatar.is_prepared = True

                    # Mark avatar as prepared after successful processing
                    if not avatar.is_prepared:
                        from src.database import get_db

                        # from sqlalchemy.orm import Session

                        # Get a new DB session in the subprocess context
                        db_gen = get_db()
                        db_session = next(db_gen)
                        try:
                            AvatarService.update_avatar_preparation_status(
                                db_session, avatar.id, "completed", True
                            )
                            avatar.is_prepared = True
                            print(f"Avatar {avatar.id} marked as prepared")
                        except Exception as e:
                            print(f"Warning: Could not update avatar status: {e}")
                        finally:
                            db_session.close()

                    # Find and move output file
                    # Note: Output path uses audio_clip_key instead of just "0"
                    avatar_output_path = os.path.join(
                        musetalk_abs_path,
                        f"results/v15/avatars/{avatar_id}/vid_output/{audio_clip_key}.mp4",
                    )

                    output_abs_path = os.path.join(original_cwd, str(output_path))

                    if os.path.exists(avatar_output_path):
                        import shutil

                        shutil.move(avatar_output_path, output_abs_path)
                        print(f"Output moved to: {output_abs_path}")
                    else:
                        print(
                            f"Warning: Expected output not found at {avatar_output_path}"
                        )
                        # Try alternative paths
                        alt_paths = [
                            os.path.join(
                                musetalk_abs_path,
                                f"results/v15/avatars/{avatar_id}/vid_output/0.mp4",
                            ),
                            os.path.join(
                                musetalk_abs_path,
                                f"results/v15/avatars/{avatar_id}/vid_output/{output_filename}.mp4",
                            ),
                        ]

                        for alt_path in alt_paths:
                            if os.path.exists(alt_path):
                                import shutil

                                shutil.move(alt_path, output_abs_path)
                                print(f"Alternative output moved to: {output_abs_path}")
                                break

                finally:
                    # Clean up temp file
                    try:
                        os.unlink(config_path)
                    except:
                        pass

                # Return relative path for web access
                try:
                    relative_path = output_path.relative_to(Path.cwd())
                    return str(relative_path).replace("\\", "/")
                except ValueError:
                    # If relative path fails, just return the filename part
                    return f"outputs/videos/{output_path.name}"

            finally:
                # Always restore original working directory
                os.chdir(original_cwd)
                # Remove MuseTalk from path
                if musetalk_abs_path in sys.path:
                    sys.path.remove(musetalk_abs_path)

        except Exception as e:
            print(f"MuseTalk error: {e}")
            # Make sure we restore working directory even on error
            try:
                os.chdir(original_cwd)
            except:
                pass
            return None

    async def generate_video(
        self,
        audio_path: str,
        avatar_video_path: str,
        output_filename: str,
        bbox_shift: int = 0,
    ) -> str:
        """Legacy method - Generate lip-sync video using MuseTalk"""

        output_path = self.output_dir / f"{output_filename}.mp4"

        try:
            # Import MuseTalk modules with proper path setup
            import sys
            import os

            # Store original working directory
            original_cwd = os.getcwd()

            # Get absolute path to MuseTalk
            musetalk_abs_path = os.path.abspath(str(self.musetalk_path))

            # Change to MuseTalk directory (important for relative imports)
            os.chdir(musetalk_abs_path)

            # Add MuseTalk to Python path
            if musetalk_abs_path not in sys.path:
                sys.path.insert(0, musetalk_abs_path)

            try:
                import subprocess
                import tempfile
                import yaml
                import sys

                # Convert paths to absolute paths
                print(f"Processing avatar path: {avatar_video_path}")
                print(f"Original working directory: {original_cwd}")

                # Fix audio path
                if not os.path.isabs(audio_path):
                    audio_abs_path = os.path.join(original_cwd, audio_path)
                else:
                    audio_abs_path = audio_path

                # Fix avatar path
                if avatar_video_path.startswith("/static/"):
                    avatar_abs_path = os.path.join(
                        original_cwd, avatar_video_path.lstrip("/")
                    )
                elif avatar_video_path.startswith("../MuseTalk/"):
                    avatar_abs_path = os.path.abspath(avatar_video_path)
                elif os.path.isabs(avatar_video_path):
                    avatar_abs_path = avatar_video_path
                else:
                    avatar_abs_path = os.path.join(original_cwd, avatar_video_path)

                # Verify files exist
                if not os.path.exists(audio_abs_path):
                    raise FileNotFoundError(f"Audio file not found: {audio_abs_path}")
                if not os.path.exists(avatar_abs_path):
                    raise FileNotFoundError(
                        f"Avatar video not found: {avatar_abs_path}"
                    )

                print(f"Audio: {audio_abs_path}")
                print(f"Avatar: {avatar_abs_path}")

                # Create avatar ID
                avatar_id = f"avatar_{output_filename}"

                # Create temporary config for realtime inference
                config_data = {
                    avatar_id: {
                        "preparation": True,
                        "video_path": avatar_abs_path,
                        "bbox_shift": bbox_shift,
                        "audio_clips": {"0": audio_abs_path},
                    }
                }

                # Create temp config file
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".yaml", delete=False
                ) as f:
                    yaml.dump(config_data, f)
                    config_path = f.name

                print(f"Created config file: {config_path}")
                print(f"Config content:")
                print(yaml.dump(config_data, default_flow_style=False))

                try:
                    # Run realtime inference via subprocess
                    print(f"Running realtime inference for avatar: {avatar_id}")

                    cmd = [
                        sys.executable,
                        "scripts/realtime_inference.py",
                        "--version",
                        "v15",
                        "--inference_config",
                        config_path,
                        "--batch_size",
                        "4",
                        "--fps",
                        "25",
                    ]

                    print(f"Command: {' '.join(cmd)}")

                    # Set environment for subprocess
                    env = os.environ.copy()
                    env["PYTHONPATH"] = musetalk_abs_path
                    env["PYTHONIOENCODING"] = "utf-8"  # Fix Unicode encoding issues

                    result = subprocess.run(
                        cmd,
                        cwd=musetalk_abs_path,
                        capture_output=False,
                        text=True,
                        env=env,  # Pass environment with PYTHONPATH
                        encoding="utf-8",  # Explicit UTF-8 encoding
                        errors="replace",  # Replace problematic characters
                    )

                    print(
                        "=================================================================="
                    )

                    if result.returncode != 0:
                        print(f"Realtime inference failed:")
                        print(f"STDOUT: {result.stdout}")
                        print(f"STDERR: {result.stderr}")
                        raise Exception(
                            f"Realtime inference process failed with code {result.returncode}"
                        )

                    print("Realtime inference completed successfully")
                    print(f"Output: {result.stdout}")

                    # Find and move output file
                    avatar_output_path = os.path.join(
                        musetalk_abs_path,
                        f"results/v15/avatars/{avatar_id}/vid_output/0.mp4",
                    )

                    output_abs_path = os.path.join(original_cwd, str(output_path))

                    if os.path.exists(avatar_output_path):
                        import shutil

                        shutil.move(avatar_output_path, output_abs_path)
                        print(f"Output moved to: {output_abs_path}")
                    else:
                        print(
                            f"Warning: Expected output not found at {avatar_output_path}"
                        )
                        # Try alternative path
                        alt_path = os.path.join(
                            musetalk_abs_path,
                            f"results/v15/avatars/{avatar_id}/vid_output/{output_filename}.mp4",
                        )
                        if os.path.exists(alt_path):
                            shutil.move(alt_path, output_abs_path)
                            print(f"Alternative output moved to: {output_abs_path}")

                finally:
                    # Clean up temp file
                    try:
                        os.unlink(config_path)
                    except:
                        pass

                return str(output_path)

            finally:
                # Always restore original working directory
                os.chdir(original_cwd)
                # Remove MuseTalk from path
                if musetalk_abs_path in sys.path:
                    sys.path.remove(musetalk_abs_path)

        except Exception as e:
            print(f"MuseTalk error: {e}")
            # Make sure we restore working directory even on error
            try:
                os.chdir(original_cwd)
            except:
                pass
            return None


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

            # Generate video using avatar system
            print(f"Generating video for {product.name} with avatar {avatar.name}...")
            video_filename = f"output_{session_id}_{product.id}"
            video_path = await self.musetalk_service.generate_video_with_avatar(
                audio_path, avatar, session_id, product.id, video_filename
            )

            # Update database
            update_data = {
                "script_text": script,
                "audio_path": audio_path,
                "video_path": video_path,
                "is_processed": True,
            }

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
