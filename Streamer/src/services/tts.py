from pathlib import Path
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s",
)
logger = logging.getLogger(__name__)


class TTSService:
    """Text-to-Speech service"""

    def __init__(self, provider: str = "gtts"):
        self.provider = provider
        self.output_dir = Path("./outputs/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def text_to_speech(self, text: str, filename: str, voice: str = "vi") -> str:
        """Convert text to speech and save as audio file"""

        output_path = self.output_dir / f"{filename}.mp3"

        try:
            if self.provider == "edge-tts":
                return await self._edge_tts(text, str(output_path), voice)
            elif self.provider == "gtts":
                return await self._google_tts(text, str(output_path), voice)
            else:
                raise ValueError(f"Unsupported TTS provider: {self.provider}")
        except Exception as e:
            logger.error(f"Error in TTS: {e}")
            return None

    async def _edge_tts(self, text: str, output_path: str, voice: str) -> str:
        """Use Edge TTS (free Microsoft TTS)"""
        try:
            import edge_tts

            logger.info(f"Starting Edge TTS with voice: {voice}")

            tts = edge_tts.Communicate(text, voice)
            await tts.save(output_path)

            logger.info(f"Audio saved successfully to: {output_path}")
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
            logger.error(f"Edge TTS error: {type(e).__name__}: {e}")
            logger.error(f"Failed to generate audio for text: {text[:50]}...")

            # Try a different voice as fallback
            if voice != "en-US-AriaNeural":
                logger.info("Trying fallback voice: en-US-AriaNeural")
                try:
                    import edge_tts

                    tts = edge_tts.Communicate(text, "en-US-AriaNeural")
                    await tts.save(output_path)
                    logger.info(f"Fallback audio saved to: {output_path}")
                    return output_path
                except Exception as fallback_error:
                    logger.error(f"Fallback voice also failed: {fallback_error}")

            return None

    async def _google_tts(self, text: str, output_path: str, lang: str) -> str:
        """Use Google TTS (gTTS - free Google TTS)"""
        try:
            from gtts import gTTS
            import asyncio

            logger.info(f"Starting Google TTS with language: {lang}")
            logger.info(f"Text to synthesize: {text[:100]}...")

            # gTTS is synchronous, so we run it in a thread pool
            def create_tts():
                tts = gTTS(text=text, lang=lang, slow=False)
                tts.save(output_path)
                return output_path

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, create_tts)

            logger.info(f"Audio saved successfully to: {output_path}")
            return result

        except ImportError:
            logger.error("gTTS not installed. Installing...")
            import subprocess

            subprocess.check_call(["pip", "install", "gtts"])

            from gtts import gTTS
            import asyncio

            def create_tts():
                tts = gTTS(text=text, lang=lang, slow=False)
                tts.save(output_path)
                return output_path

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, create_tts)
            return result

        except Exception as e:
            logger.error(f"Google TTS error: {type(e).__name__}: {e}")
            logger.error(f"Failed to generate audio for text: {text[:50]}...")

            # Try English as fallback
            if lang != "en":
                logger.info("Trying fallback language: en")
                try:
                    from gtts import gTTS
                    import asyncio

                    def create_fallback_tts():
                        tts = gTTS(text=text, lang="en", slow=False)
                        tts.save(output_path)
                        return output_path

                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, create_fallback_tts)
                    logger.info(f"Fallback audio saved to: {output_path}")
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback language also failed: {fallback_error}")

            return None
