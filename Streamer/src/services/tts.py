from pathlib import Path
import logging


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s")
logger = logging.getLogger(__name__)

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
            logger.error(f"Error in TTS: {e}")
            return None

    async def _edge_tts(self, text: str, output_path: str, voice: str) -> str:
        """Use Edge TTS (free Microsoft TTS)"""
        try:
            import edge_tts

            tts = edge_tts.Communicate(text, voice)
            await tts.save(output_path)
            return output_path
        except ImportError:
            logger.error("edge-tts not installed. Installing...")
            import subprocess

            subprocess.check_call(["pip", "install", "edge-tts"])

            import edge_tts

            tts = edge_tts.Communicate(text, voice)
            await tts.save(output_path)
            return output_path
        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            return None


