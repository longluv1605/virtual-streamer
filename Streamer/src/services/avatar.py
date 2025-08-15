import os
import cv2
import torch
import glob
import pickle
import sys
from tqdm import tqdm
import json

import shutil
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def osmakedirs(path_list):
    for path in path_list:
        os.makedirs(path) if not os.path.exists(path) else None


def video2imgs(vid_path, save_path, ext='.png', cut_frame=10000000):
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
    musetalk_path = "../MuseTalk"
    
    def __init__(self, avatar_id, video_path, preparation, fp, vae, bbox_shift=0, batch_size=4, version="v15", extra_margin=10, parsing_mode="jaw"):
        self.version = version
        self.extra_margin = extra_margin
        self.parsing_mode = parsing_mode
        
        self.avatar_id = avatar_id
        self.video_path = video_path
        self.bbox_shift = bbox_shift
        
        cwd = os.getcwd()
        self.avatar_path = os.path.join(cwd, f"./results/avatars/avatar_{avatar_id}")
        self.full_imgs_path = f"{self.avatar_path}/full_imgs"
        self.coords_path = f"{self.avatar_path}/coords.pkl"
        self.latents_out_path = f"{self.avatar_path}/latents.pt"
        self.video_out_path = f"{self.avatar_path}/vid_output/"
        self.mask_out_path = f"{self.avatar_path}/mask"
        self.mask_coords_path = f"{self.avatar_path}/mask_coords.pkl"
        self.avatar_info_path = f"{self.avatar_path}/avator_info.json"
        self.avatar_info = {
            "avatar_id": avatar_id,
            "video_path": video_path,
            "bbox_shift": bbox_shift,
            "version": self.version
        }
        self.preparation = preparation
        self.batch_size = batch_size
        self.idx = 0
        
        self.fp = fp
        self.vae = vae
        self.init()

    def init(self):
        try:
            # Setup paths
            musetalk_abs_path = os.path.abspath(str(self.musetalk_path))
            original_cwd = os.getcwd()

            # Change to MuseTalk directory for imports
            os.chdir(musetalk_abs_path)
            if musetalk_abs_path not in sys.path:
                sys.path.insert(0, musetalk_abs_path)
                     
            from musetalk.utils.preprocessing import read_imgs
            
            if self.preparation:
                if os.path.exists(self.avatar_path):
                    response = input(f"{self.avatar_id} exists, Do you want to re-create it ? (y/n)")
                    if response.lower() == "y":
                        shutil.rmtree(self.avatar_path)
                        logger.info("*********************************")
                        logger.info(f"  Creating avator: {self.avatar_id}")
                        logger.info("*********************************")
                        osmakedirs([self.avatar_path, self.full_imgs_path, self.video_out_path, self.mask_out_path])
                        self.prepare_material()
                    else:
                        self.input_latent_list_cycle = torch.load(self.latents_out_path)
                        with open(self.coords_path, 'rb') as f:
                            self.coord_list_cycle = pickle.load(f)
                        input_img_list = glob.glob(os.path.join(self.full_imgs_path, '*.[jpJP][pnPN]*[gG]'))
                        input_img_list = sorted(input_img_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
                        self.frame_list_cycle = read_imgs(input_img_list)
                        with open(self.mask_coords_path, 'rb') as f:
                            self.mask_coords_list_cycle = pickle.load(f)
                        input_mask_list = glob.glob(os.path.join(self.mask_out_path, '*.[jpJP][pnPN]*[gG]'))
                        input_mask_list = sorted(input_mask_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
                        self.mask_list_cycle = read_imgs(input_mask_list)
                else:
                    logger.info("*********************************")
                    logger.info(f"  creating avator: {self.avatar_id}")
                    logger.info("*********************************")
                    osmakedirs([self.avatar_path, self.full_imgs_path, self.video_out_path, self.mask_out_path])
                    self.prepare_material()
            else:
                if not os.path.exists(self.avatar_path):
                    logger.warning(f"{self.avatar_id} does not exist, you should set preparation to True")
                    sys.exit()

                with open(self.avatar_info_path, "r") as f:
                    avatar_info = json.load(f)

                if avatar_info['bbox_shift'] != self.avatar_info['bbox_shift']:
                    response = input(f" 【bbox_shift】 is changed, you need to re-create it ! (c/continue)")
                    if response.lower() == "c":
                        shutil.rmtree(self.avatar_path)
                        logger.info("*********************************")
                        logger.info(f"  creating avator: {self.avatar_id}")
                        logger.info("*********************************")
                        osmakedirs([self.avatar_path, self.full_imgs_path, self.video_out_path, self.mask_out_path])
                        self.prepare_material()
                    else:
                        sys.exit()
                else:
                    self.input_latent_list_cycle = torch.load(self.latents_out_path)
                    with open(self.coords_path, 'rb') as f:
                        self.coord_list_cycle = pickle.load(f)
                    input_img_list = glob.glob(os.path.join(self.full_imgs_path, '*.[jpJP][pnPN]*[gG]'))
                    input_img_list = sorted(input_img_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
                    self.frame_list_cycle = read_imgs(input_img_list)
                    with open(self.mask_coords_path, 'rb') as f:
                        self.mask_coords_list_cycle = pickle.load(f)
                    input_mask_list = glob.glob(os.path.join(self.mask_out_path, '*.[jpJP][pnPN]*[gG]'))
                    input_mask_list = sorted(input_mask_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
                    self.mask_list_cycle = read_imgs(input_mask_list)
                    
            # Restore working directory
            os.chdir(original_cwd)
            
            from src.database import get_db

            # from sqlalchemy.orm import Session

            # Get a new DB session in the subprocess context
            db_gen = get_db()
            db_session = next(db_gen)
            try:
                from ..database import AvatarDatabaseService
                AvatarDatabaseService.update_avatar_preparation_status(
                    db_session, self.avatar_id, True
                )
                logger.info(f"Avatar {self.avatar_id} marked as prepared...")
            except Exception as e:
                logger.error(f"Warning: Could not update avatar status: {e}")
            finally:
                db_session.close()
            
        except Exception as e:
            logger.error(f"Failed to prepare avatar: {e}")
            # Restore working directory on error
            try:
                os.chdir(original_cwd)
            except:
                pass
            return False

    def prepare_material(self):
        try:
            from musetalk.utils.preprocessing import get_landmark_and_bbox
            from musetalk.utils.blending import get_image_prepare_material
        
            logger.info("preparing data materials ... ...")
            with open(self.avatar_info_path, "w") as f:
                json.dump(self.avatar_info, f)

            if os.path.isfile(self.video_path):
                video2imgs(self.video_path, self.full_imgs_path, ext='png')
            else:
                logger.info(f"copy files in {self.video_path}")
                files = os.listdir(self.video_path)
                files.sort()
                files = [file for file in files if file.split(".")[-1] == "png"]
                for filename in files:
                    shutil.copyfile(f"{self.video_path}/{filename}", f"{self.full_imgs_path}/{filename}")
            input_img_list = sorted(glob.glob(os.path.join(self.full_imgs_path, '*.[jpJP][pnPN]*[gG]')))

            logger.info("extracting landmarks...")
            coord_list, frame_list = get_landmark_and_bbox(input_img_list, self.bbox_shift)
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
                resized_crop_frame = cv2.resize(crop_frame, (256, 256), interpolation=cv2.INTER_LANCZOS4)
                latents = self.vae.get_latents_for_unet(resized_crop_frame)
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
                mask, crop_box = get_image_prepare_material(frame, [x1, y1, x2, y2], fp=self.fp, mode=mode)

                cv2.imwrite(f"{self.mask_out_path}/{str(i).zfill(8)}.png", mask)
                self.mask_coords_list_cycle += [crop_box]
                self.mask_list_cycle.append(mask)

            with open(self.mask_coords_path, 'wb') as f:
                pickle.dump(self.mask_coords_list_cycle, f)

            with open(self.coords_path, 'wb') as f:
                pickle.dump(self.coord_list_cycle, f)

            torch.save(self.input_latent_list_cycle, os.path.join(self.latents_out_path))
        except Exception as e:
            logger.error('Prepare material failed...', e)