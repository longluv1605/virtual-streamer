import os
import cv2
import torch
import glob
import copy
import pickle
import sys
from tqdm import tqdm
import json
import time
import queue
import threading
import numpy as np
import subprocess

import shutil
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s",
)
logger = logging.getLogger(__name__)


def osmakedirs(path_list):
    for path in path_list:
        os.makedirs(path) if not os.path.exists(path) else None


def video2imgs(vid_path, save_path, ext=".png", cut_frame=10000000):
    cap = cv2.VideoCapture(vid_path)
    count = 0
    while True:
        if count > cut_frame:
            break
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(f"{save_path}/{count:08d}.png", frame)
            count += 1
        else:
            break


class Avatar:
    base_path = "../Streamer"
    musetalk_path = "../MuseTalk"
    active = False

    def __init__(
        self,
        avatar_id,
        video_path,
        preparation=False,
        bbox_shift=0,
        version="v15",
        extra_margin=10,
        parsing_mode="jaw",
        audio_padding_length_left=2,
        audio_padding_length_right=2, 
        compress=False,
        compress_resolution=None, 
        compress_fps=None, 
        compress_bitrate=None
    ):
        self.version = version
        self.extra_margin = extra_margin
        self.parsing_mode = parsing_mode
        self.audio_padding_length_left = audio_padding_length_left
        self.audio_padding_length_right = audio_padding_length_right

        self.avatar_id = avatar_id
        self.bbox_shift = bbox_shift
        
        self.video_path = video_path

        cwd = os.getcwd()
        self.avatar_path = os.path.join(cwd, f"./results/avatars/avatar_{avatar_id}")
        self.full_imgs_path = f"{self.avatar_path}/full_imgs"
        self.coords_path = f"{self.avatar_path}/coords.pkl"
        self.latents_out_path = f"{self.avatar_path}/latents.pt"
        self.video_out_path = f"{self.avatar_path}/vid_output/"
        self.mask_out_path = f"{self.avatar_path}/mask"
        self.mask_coords_path = f"{self.avatar_path}/mask_coords.pkl"
        self.avatar_info_path = f"{self.avatar_path}/avator_info.json"
        
        # Preprocessing video
        if compress:
            if not compress_resolution or not compress_fps or not compress_bitrate:
                raise ValueError("Compress is required but missing attribute!")
            self._preprocess_avatar_video(compress_resolution, compress_fps, compress_bitrate)
        
        self.avatar_info = {
            "avatar_id": avatar_id,
            "video_path": self.video_path,
            "bbox_shift": bbox_shift,
            "version": self.version,
        }
        self.preparation = preparation
        self.idx = 0
        

    def _preprocess_avatar_video(self, target_width=480, fps=25, bitrate_kbps=500):
        """
        Giảm độ phân giải, fps và bitrate cho video avatar.

        :param input_path: Đường dẫn video gốc.
        :param output_path: Nơi lưu video đã nén.
        :param target_width: Chiều rộng mong muốn (tự giữ tỷ lệ).
        :param fps: Số khung hình mỗi giây mong muốn.
        :param bitrate_kbps: Bitrate mục tiêu (kb/s).
        """
        
        try:
            logger.info("Preprocessing avatar video...")
            output_path = f"{self.video_path}.compressed.mp4"
            
            # Đảm bảo thư mục đích tồn tại
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cmd = [
                "ffmpeg", "-y", "-i", self.video_path,
                "-vf", f"scale={target_width}:-2,fps={fps}",
                "-b:v", f"{bitrate_kbps}k",
                "-c:v", "libx264", "-preset", "fast",
                "-movflags", "+faststart",  # tối ưu streaming qua mạng
                "-an",  # Bỏ track audio nếu không cần (avatar thường không cần âm thanh)
                output_path
            ]
            subprocess.run(cmd, check=True)
            self.video_path = output_path
            self._update_avatar_status(video_path=self.video_path)
        except Exception as e:
            logger.error("Error")

    def prepare_avatar(self, fp, vae):
        try:
            # Setup paths
            musetalk_abs_path = os.path.abspath(str(self.musetalk_path))
            original_cwd = os.getcwd()

            # Change to MuseTalk directory for imports
            os.chdir(musetalk_abs_path)
            if musetalk_abs_path not in sys.path:
                sys.path.insert(0, musetalk_abs_path)
            
            if not self.active:
                if self.preparation:
                    if not os.path.exists(self.avatar_path):
                        self._create_avatar(fp, vae)
                else:
                    if not os.path.exists(self.avatar_path):
                        logger.warning(
                            f"Avatar path for {self.avatar_id} does not exist; forcing re-creation (preparation set False)."
                        )
                        self._create_avatar(fp, vae)
                    else:
                        avatar_info = self._read_avatar_info()
                        if avatar_info is None:
                            # Corrupted or unreadable file – rebuild
                            logger.warning(
                                f"Avatar info file corrupted/unreadable for {self.avatar_id}; re-creating avatar data."
                            )
                            self.preparation = True
                            self._create_avatar(fp, vae)
                        elif avatar_info.get("bbox_shift") != self.avatar_info.get("bbox_shift"):
                            logger.warning("bbox_shift is changed, forcing re-creation.")
                            self._create_avatar(fp, vae)
                        else:
                            self._load_avatar()
                        
            self.preparation = False
            self.active = True
            # Restore working directory
            os.chdir(original_cwd)
            self._update_avatar_status(is_prepared=True)
            return True

        except Exception as e:
            logger.error(f"Failed to prepare avatar: {e}")
            # Restore working directory on error
            try:
                os.chdir(original_cwd)
            except:
                pass
            return False
    
    def _create_avatar(self, fp, vae):
        # Remove any existing (possibly corrupted) directory
        if os.path.isdir(self.avatar_path):
            try:
                shutil.rmtree(self.avatar_path)
            except Exception as e:
                logger.warning(f"Could not remove existing avatar directory: {e}")
        logger.info(f"***** Creating avator: [{self.avatar_id}] with video = {self.video_path}  ******")
        osmakedirs(
            [
                self.avatar_path,
                self.full_imgs_path,
                self.video_out_path,
                self.mask_out_path,
            ]
        )
        self._prepare_material(fp, vae)

    def _read_avatar_info(self):
        try:
            with open(self.avatar_info_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(
                f"JSON decode error reading avatar info ({self.avatar_info_path}): {e}"
            )
            return None
        except FileNotFoundError:
            logger.error(f"Avatar info file missing: {self.avatar_info_path}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading avatar info: {e}")
            return None

    def _load_avatar(self):
        try:
            logger.info(f"***** Loading prepared avatar [{self.avatar_id}] *****")
            from musetalk.utils.preprocessing import read_imgs

            self.input_latent_list_cycle = torch.load(self.latents_out_path)
            with open(self.coords_path, "rb") as f:
                self.coord_list_cycle = pickle.load(f)
            input_img_list = glob.glob(
                os.path.join(self.full_imgs_path, "*.[jpJP][pnPN]*[gG]")
            )
            input_img_list = sorted(
                input_img_list,
                key=lambda x: int(os.path.splitext(os.path.basename(x))[0]),
            )
            self.frame_list_cycle = read_imgs(input_img_list)
            with open(self.mask_coords_path, "rb") as f:
                self.mask_coords_list_cycle = pickle.load(f)
            input_mask_list = glob.glob(
                os.path.join(self.mask_out_path, "*.[jpJP][pnPN]*[gG]")
            )
            input_mask_list = sorted(
                input_mask_list,
                key=lambda x: int(os.path.splitext(os.path.basename(x))[0]),
            )
            self.mask_list_cycle = read_imgs(input_mask_list)
            self._update_avatar_status()
        except Exception as e:
            logger.error(f"Failed loading avatar...: {e}")
            raise

    def _update_avatar_status(self, video_path=None, is_prepared=None):
        from src.database import get_db

        # Get a new DB session in the subprocess context
        db_gen = get_db()
        db_session = next(db_gen)
        try:
            from ..database import AvatarDatabaseService

            if video_path is not None:
                AvatarDatabaseService.update_avatar_preparation_status(
                    db_session, self.avatar_id, video_path=video_path
                )
                logger.info(f"Avatar {self.avatar_id} video path is updated to {video_path}")
            if is_prepared is not None:
                AvatarDatabaseService.update_avatar_preparation_status(
                    db_session, self.avatar_id, is_prepared=is_prepared
                )
                logger.info(f"Avatar {self.avatar_id} is marked as prepared")
        except Exception as e:
            logger.error(f"Warning: Could not update avatar status: {e}")
        finally:
            db_session.close()

    def _prepare_material(self, fp, vae):
        try:
            from musetalk.utils.preprocessing import get_landmark_and_bbox
            from musetalk.utils.blending import get_image_prepare_material

            logger.info("preparing data materials ... ...")
            # Atomic write of avatar info to avoid truncation on crash
            tmp_path = f"{self.avatar_info_path}.tmp"
            try:
                with open(tmp_path, "w") as f:
                    json.dump(self.avatar_info, f)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, self.avatar_info_path)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

            if os.path.isfile(self.video_path):
                video2imgs(self.video_path, self.full_imgs_path, ext="png")
            else:
                logger.info(f"copy files in {self.video_path}")
                files = os.listdir(self.video_path)
                files.sort()
                files = [file for file in files if file.split(".")[-1] == "png"]
                for filename in files:
                    shutil.copyfile(
                        f"{self.video_path}/{filename}",
                        f"{self.full_imgs_path}/{filename}",
                    )
            input_img_list = sorted(
                glob.glob(os.path.join(self.full_imgs_path, "*.[jpJP][pnPN]*[gG]"))
            )

            logger.info("extracting landmarks...")
            coord_list, frame_list = get_landmark_and_bbox(
                input_img_list, self.bbox_shift
            )
            input_latent_list = []
            idx = -1

            # maker if the bbox is not sufficient
            coord_placeholder = (0.0, 0.0, 0.0, 0.0)
            for bbox, frame in zip(coord_list, frame_list):
                idx = idx + 1
                if bbox == coord_placeholder:
                    continue
                x1, y1, x2, y2 = bbox
                if self.version == "v15":
                    y2 = y2 + self.extra_margin
                    y2 = min(y2, frame.shape[0])
                    coord_list[idx] = [x1, y1, x2, y2]
                crop_frame = frame[y1:y2, x1:x2]
                resized_crop_frame = cv2.resize(
                    crop_frame, (256, 256), interpolation=cv2.INTER_LANCZOS4
                )
                latents = vae.get_latents_for_unet(resized_crop_frame)
                input_latent_list.append(latents)

            self.frame_list_cycle = frame_list + frame_list[::-1]
            self.coord_list_cycle = coord_list + coord_list[::-1]
            self.input_latent_list_cycle = input_latent_list + input_latent_list[::-1]
            self.mask_coords_list_cycle = []
            self.mask_list_cycle = []

            for i, frame in enumerate(tqdm(self.frame_list_cycle)):
                cv2.imwrite(f"{self.full_imgs_path}/{str(i).zfill(8)}.png", frame)

                x1, y1, x2, y2 = self.coord_list_cycle[i]
                if self.version == "v15":
                    mode = self.parsing_mode
                else:
                    mode = "raw"
                mask, crop_box = get_image_prepare_material(
                    frame, [x1, y1, x2, y2], fp=fp, mode=mode
                )

                cv2.imwrite(f"{self.mask_out_path}/{str(i).zfill(8)}.png", mask)
                self.mask_coords_list_cycle += [crop_box]
                self.mask_list_cycle.append(mask)

            with open(self.mask_coords_path, "wb") as f:
                pickle.dump(self.mask_coords_list_cycle, f)

            with open(self.coords_path, "wb") as f:
                pickle.dump(self.coord_list_cycle, f)

            torch.save(
                self.input_latent_list_cycle, os.path.join(self.latents_out_path)
            )
        except Exception as e:
            logger.error(f"Prepare material failed: {e}")
            raise e

    @torch.no_grad()
    def inference(
        self,
        video_queue,
        audio_path,
        fps,
        batch_size,
        unet,
        vae,
        pe,
        timesteps,
        whisper,
        audio_processor,
        weight_dtype,
        device,
    ):
        try:
            logger.info("Start inference ...")
            ############################################## extract audio feature ##############################################
            start_time = time.time()
            whisper_chunks = self._extract_audio_feature(
                audio_path, audio_processor, whisper, weight_dtype, fps, device
            )

            if whisper_chunks is None or len(whisper_chunks) == 0:
                raise ValueError("Failed to extract audio features")

            logger.info(
                f"processing audio:{audio_path} costs {(time.time() - start_time) * 1000}ms"
            )
            ############################################## inference batch by batch ##############################################
            video_num = len(whisper_chunks)
            self._generate(
                video_queue,
                unet,
                vae,
                pe,
                timesteps,
                video_num,
                whisper_chunks,
                batch_size,
                device,
            )

            logger.info(
                "Total process time of {} frames = {}s".format(
                    video_num, time.time() - start_time
                )
            )
        except Exception as e:
            logger.error(f"Error in inference: {e}")
            raise  # Re-raise the exception to propagate it

    def _extract_audio_feature(
        self, audio_path, audio_processor, whisper, weight_dtype, fps, device
    ):
        try:
            logger.info("Creating audio features...")
            logger.info(f"Audio path: {audio_path}")
            logger.info(f"Audio file exists: {os.path.exists(audio_path)}")

            # Extract audio features
            result = audio_processor.get_audio_feature(
                audio_path, weight_dtype=weight_dtype
            )

            if result is None:
                logger.error(f"Audio processor returned None for file: {audio_path}")
                return None

            whisper_input_features, librosa_length = result
            whisper_chunks = audio_processor.get_whisper_chunk(
                whisper_input_features,
                device,
                weight_dtype,
                whisper,
                librosa_length,
                fps=fps,
                audio_padding_length_left=self.audio_padding_length_left,
                audio_padding_length_right=self.audio_padding_length_right,
            )
            return whisper_chunks
        except Exception as e:
            logger.error(f"Error creating audio features: {e}")
            return None

    def _generate(
        self,
        video_queue,
        unet,
        vae,
        pe,
        timesteps,
        video_num,
        whisper_chunks,
        batch_size,
        device,
    ):
        try:
            # Setup paths
            musetalk_abs_path = os.path.abspath(str(self.musetalk_path))
            original_cwd = os.getcwd()

            # Change to MuseTalk directory for imports
            os.chdir(musetalk_abs_path)
            if musetalk_abs_path not in sys.path:
                sys.path.insert(0, musetalk_abs_path)

            from musetalk.utils.utils import datagen

            res_frame_queue = queue.Queue()
            self.idx = 0
            # Create a sub-thread and start it
            process_thread = threading.Thread(
                target=self._process_frames,
                args=(video_queue, res_frame_queue, video_num),
            )
            process_thread.start()

            gen = datagen(whisper_chunks, self.input_latent_list_cycle, batch_size)

            for _, (whisper_batch, latent_batch) in enumerate(
                tqdm(gen, total=int(np.ceil(float(video_num) / batch_size)))
            ):
                audio_feature_batch = pe(whisper_batch.to(device))
                latent_batch = latent_batch.to(device=device, dtype=unet.model.dtype)

                pred_latents = unet.model(
                    latent_batch, timesteps, encoder_hidden_states=audio_feature_batch
                ).sample
                pred_latents = pred_latents.to(device=device, dtype=vae.vae.dtype)
                recon = vae.decode_latents(pred_latents)
                for res_frame in recon:
                    res_frame_queue.put(res_frame)
            # Close the queue and sub-thread after all tasks are completed
            process_thread.join()
            os.chdir(original_cwd)
        except Exception as e:
            try:
                os.chdir(original_cwd)
            except:
                pass
            logger.error(f"Error in _generate: {e}")
            raise  # Re-raise to propagate error

    def _process_frames(self, video_queue, res_frame_queue, video_len):
        try:
            while True:
                from musetalk.utils.blending import get_image_blending

                if self.idx >= video_len - 1:
                    break
                try:
                    res_frame = res_frame_queue.get(block=True, timeout=1)
                except queue.Empty:
                    continue

                bbox = self.coord_list_cycle[self.idx % (len(self.coord_list_cycle))]
                ori_frame = copy.deepcopy(
                    self.frame_list_cycle[self.idx % (len(self.frame_list_cycle))]
                )
                x1, y1, x2, y2 = bbox
                try:
                    res_frame = cv2.resize(
                        res_frame.astype(np.uint8), (x2 - x1, y2 - y1)
                    )
                except:
                    continue
                mask = self.mask_list_cycle[self.idx % (len(self.mask_list_cycle))]
                mask_crop_box = self.mask_coords_list_cycle[
                    self.idx % (len(self.mask_coords_list_cycle))
                ]
                combine_frame = get_image_blending(
                    ori_frame, res_frame, bbox, mask, mask_crop_box
                )

                try:
                    video_queue.put(
                        (self.idx, combine_frame), timeout=0.1
                    )
                except:
                    # Queue full, drop frame
                    pass

                self.idx = self.idx + 1
            self.idx = 0
        except Exception as e:
            raise RuntimeError(f"Error process_frames: {e}")
