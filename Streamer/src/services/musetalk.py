import os
import sys
from pathlib import Path
import threading

from src.models import Avatar
from ..database.avatar import AvatarDatabaseService
from .avatar import Avatar

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s",
)
logger = logging.getLogger(__name__)


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
            logger.warning(
                f"Warning: MuseTalk setup incomplete. Missing files/directories:"
            )
            for missing in missing_files:
                logger.warning(f"  - {missing}")
            logger.warning(
                f"Please ensure MuseTalk is properly installed at: {musetalk_abs_path}"
            )
        else:
            logger.info(f"MuseTalk setup validated at: {musetalk_abs_path}")

    async def generate_video_with_avatar(
        self,
        audio_path: str,
        stream_fps: int,
        batch_size: int,
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
                # logger.(f"Processing avatar: {avatar.name} (ID: {avatar.id})")
                # logger.(f"Avatar path: {avatar.video_path}")
                # logger.(f"Original working directory: {original_cwd}")

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

                logger.info(f"Audio: {audio_abs_path}")
                logger.info(f"Avatar: {avatar_abs_path}")
                logger.info(f"MuseTalk models verified")

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

                logger.info(f"Created config file: {config_path}")
                logger.info(f"Config content:")
                logger.info(yaml.dump(config_data, default_flow_style=False))
                logger.info(f"Avatar preparation needed: {not avatar.is_prepared}")

                try:
                    # Run realtime inference via subprocess
                    logger.info(f"Running realtime inference for avatar: {avatar_id}")
                    logger.info(f"Audio clip key: {audio_clip_key}")

                    cmd = [
                        sys.executable,
                        "scripts/realtime_inference.py",
                        "--version",
                        "v15",
                        "--inference_config",
                        config_path,
                        "--batch_size",
                        str(batch_size),
                        "--fps",
                        str(stream_fps),
                    ]

                    logger.info(f"Command: {' '.join(cmd)}")

                    # Set environment for subprocess
                    env = os.environ.copy()
                    env["PYTHONPATH"] = musetalk_abs_path
                    env["PYTHONIOENCODING"] = "utf-8"  # Fix Unicode encoding issues

                    # Add CUDA settings for better memory management
                    env["CUDA_VISIBLE_DEVICES"] = "0"  # Use first GPU
                    env["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"

                    logger.info("Starting MuseTalk inference process...")
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

                    logger.info(
                        "=================================================================="
                    )

                    if result.returncode != 0:
                        logger.warning(f"Realtime inference failed:")
                        logger.warning(f"STDOUT: {result.stdout}")
                        logger.warning(f"STDERR: {result.stderr}")
                        raise Exception(
                            f"Realtime inference process failed with code {result.returncode}"
                        )

                    logger.info("Realtime inference completed successfully")
                    logger.info(f"Output: {result.stdout}")
                    avatar.is_prepared = True

                    # Mark avatar as prepared after successful processing
                    if not avatar.is_prepared:
                        from src.database import get_db

                        # from sqlalchemy.orm import Session

                        # Get a new DB session in the subprocess context
                        db_gen = get_db()
                        db_session = next(db_gen)
                        try:
                            AvatarDatabaseService.update_avatar_preparation_status(
                                db_session, avatar.id, True
                            )
                            avatar.is_prepared = True
                            logger.info(f"Avatar {avatar.id} marked as prepared")
                        except Exception as e:
                            logger.error(
                                f"Warning: Could not update avatar status: {e}"
                            )
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
                        logger.info(f"Output moved to: {output_abs_path}")
                    else:
                        logger.warning(
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
                                logger.info(
                                    f"Alternative output moved to: {output_abs_path}"
                                )
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
            logger.error(f"MuseTalk error: {e}")
            # Make sure we restore working directory even on error
            try:
                os.chdir(original_cwd)
            except:
                pass
            return None


class MuseTalkRealtimeService:
    """
    Service để chạy MuseTalk realtime cho WebRTC streaming
    Load models một lần và cache avatar data
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # Singleton pattern để chỉ load models một lần
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self.device = None
        self.vae = None
        self.unet = None
        self.pe = None
        self.whisper = None
        self.audio_processor = None
        self.fp = None
        self.timesteps = None
        self.weight_dtype = None

        self._initialized = False
        self._models_loaded = False
        self.musetalk_path = Path("../MuseTalk")
        self._avatars = {}
        self._current_avatar = None  # track currently active avatar

    def initialize_models(self, gpu_id=0, version="v15"):
        """
        Load tất cả MuseTalk models một lần duy nhất khi khởi động server
        """
        if self._models_loaded:
            logger.info("MuseTalk models already loaded")
            return True

        logger.info("Loading MuseTalk models for realtime...")

        try:
            import torch
            from transformers import WhisperModel

            # Setup paths
            musetalk_abs_path = os.path.abspath(str(self.musetalk_path))
            original_cwd = os.getcwd()

            # Change to MuseTalk directory for imports
            os.chdir(musetalk_abs_path)
            if musetalk_abs_path not in sys.path:
                sys.path.insert(0, musetalk_abs_path)

            # Setup device
            self.device = torch.device(
                f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
            )
            logger.info(f"Using device: {self.device}")

            # Import MuseTalk modules
            from musetalk.utils.utils import load_all_model
            from musetalk.utils.audio_processor import AudioProcessor
            from musetalk.utils.face_parsing import FaceParsing

            # Load main models
            logger.info("Loading VAE, UNet, PositionalEncoding...")
            self.vae, self.unet, self.pe = load_all_model(
                unet_model_path="./models/musetalk/pytorch_model.bin",
                vae_type="sd-vae",
                unet_config="./models/musetalk/musetalk.json",
                device=self.device,
            )

            # Move to half precision and device
            self.pe = self.pe.half().to(self.device)
            self.vae.vae = self.vae.vae.half().to(self.device)
            self.unet.model = self.unet.model.half().to(self.device)

            # Setup timesteps
            self.timesteps = torch.tensor([0], device=self.device)
            self.weight_dtype = self.unet.model.dtype

            # Load Whisper
            logger.info("Loading Whisper model...")
            self.audio_processor = AudioProcessor(
                feature_extractor_path="./models/whisper"
            )
            self.whisper = WhisperModel.from_pretrained("./models/whisper")
            self.whisper = self.whisper.to(
                device=self.device, dtype=self.weight_dtype
            ).eval()
            self.whisper.requires_grad_(False)

            # Load Face Parser
            logger.info("Loading Face Parser...")
            if version == "v15":
                self.fp = FaceParsing(left_cheek_width=90, right_cheek_width=90)
            else:
                self.fp = FaceParsing()

            # Restore working directory
            os.chdir(original_cwd)

            self._models_loaded = True
            self._initialized = True
            logger.info("MuseTalk realtime models loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load MuseTalk models: {e}")
            # Restore working directory on error
            try:
                os.chdir(original_cwd)
            except:
                pass
            return False

    def prepare_avatar(
        self,
        avatar_id: int,
        video_path: str,
        preparation: bool = True,
        fps: int = 25,
        batch_size: int = 4,
    ) -> bool:
        """
        Sử dụng Avatar class có sẵn từ MuseTalk để prepare avatar data
        """
        if not self._models_loaded:
            logger.warning("Models not loaded. Call initialize_models() first.")
            return False

        key = str(avatar_id)

        # Check if avatar already prepared
        if key in self._avatars:
            logger.info(f"Avatar {avatar_id} already prepared (cache hit)")
            self._current_avatar = key
            return True

        logger.info(f"Preparing avatar: {avatar_id}")
        logger.info(f"  video_path={video_path} preparation={preparation}")

        try:
            avatar_obj = Avatar(avatar_id, video_path, preparation)
            success = avatar_obj.prepare_avatar(self.fp, self.vae)
        except Exception as e:
            # Log full error; often JSON errors surface here
            logger.error(
                f"Exception during Avatar.prepare_avatar(): {e}", exc_info=True
            )
            return False

        if success:
            self._avatars[key] = avatar_obj
            self._current_avatar = key
            logger.info(f"[Avatar {avatar_id}] prepared successfully.")
            return True
        else:
            logger.error(f"[Avatar {avatar_id}] preparation returned False")
            return False

    def generate_frames_for_webrtc(
        self,
        audio_path: str,
        video_queue,
        audio_queue,
        fps: int = 25,
        batch_size: int = 4,
    ):
        """
        Sử dụng logic có sẵn từ MuseTalk để generate frames cho WebRTC
        """
        if not self._models_loaded:
            logger.warning("Models not loaded. Call initialize_models() first.")
            return

        if not self._current_avatar or self._current_avatar not in self._avatars:
            logger.warning("No avatar prepared. Call prepare_avatar() first.")
            return

        logger.info(f"Starting realtime generation for audio: {audio_path}")
        try:
            # Convert relative audio path to absolute before changing directories
            if not os.path.isabs(audio_path):
                audio_path = os.path.abspath(audio_path)

            musetalk_abs_path = os.path.abspath(str(self.musetalk_path))
            original_cwd = os.getcwd()
            os.chdir(musetalk_abs_path)

            current_avatar = self.get_current_avatar()
            current_avatar.inference(
                video_queue,
                audio_queue,
                audio_path,
                fps,
                batch_size,
                self.unet,
                self.vae,
                self.pe,
                self.timesteps,
                self.whisper,
                self.audio_processor,
                self.weight_dtype,
                self.device,
            )

            logger.info("Realtime generation completed successfully")
        except Exception as e:
            logger.error(f"Realtime generation failed: {e}", exc_info=True)
            raise  # Re-raise exception to propagate failure
        finally:
            try:
                os.chdir(original_cwd)
            except:
                pass

    def is_ready(self):
        """Check xem models đã load chưa"""
        return self._models_loaded

    def get_current_avatar(self):
        """Get avatar hiện tại"""
        return self._avatars[self._current_avatar]


# Singleton instance
_musetalk_realtime_service = None


def get_musetalk_realtime_service():
    """Get singleton instance của MuseTalk Realtime Service"""
    logger.info("Getting Musetalk Realtime ...")
    global _musetalk_realtime_service
    if _musetalk_realtime_service is None:
        _musetalk_realtime_service = MuseTalkRealtimeService()
    return _musetalk_realtime_service


def initialize_musetalk_on_startup():
    """
    Hàm để gọi khi khởi động server - load models một lần
    """
    try:
        service = get_musetalk_realtime_service()
        return service.initialize_models()
    except Exception as e:
        logger.error(f"Failed to initialize MuseTalk on startup: {e}")
        return False
