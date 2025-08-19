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

        if not audio_path:
            logger.error("Audio path is None or empty. Cannot generate frames.")
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
