import os
from pathlib import Path
from src.models import Avatar

from ..database.avatar import AvatarService

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
                # print(f"Processing avatar: {avatar.name} (ID: {avatar.id})")
                # print(f"Avatar path: {avatar.video_path}")
                # print(f"Original working directory: {original_cwd}")

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
                        str(batch_size),
                        "--fps",
                        str(stream_fps),
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
