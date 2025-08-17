import asyncio
import fractions
import threading
from queue import Queue, Empty
from typing import Dict, Optional, Tuple

import numpy as np
from av import VideoFrame
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    MediaStreamTrack,
)
from aiortc.contrib.media import MediaBlackhole

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s",
)
logger = logging.getLogger(__name__)


VideoItem = Tuple[int, np.ndarray]  # (frame_idx, bgr_frame[h,w,3])


class VideoTrack(MediaStreamTrack):
    """Video track lấy frame từ Queue để gửi qua WebRTC."""

    kind = "video"

    def __init__(self, queue: Queue, fps: int):
        super().__init__()
        self._queue = queue
        self._fps = fps
        self._loop = asyncio.get_running_loop()

    async def recv(self) -> VideoFrame:
        """Nhận frame từ Queue và trả về VideoFrame."""
        try:
            item: VideoItem = await self._loop.run_in_executor(None, self._queue.get)
            idx, frame = item
            vf = VideoFrame.from_ndarray(frame, format="bgr24")
            vf.pts = idx
            vf.time_base = fractions.Fraction(1, self._fps)
            return vf
        except Exception as e:
            logger.error("VideoTrack recv error: %s", e)
            raise


class WebRTCSession:
    """
    Lưu trữ queue và PeerConnection cho một phiên WebRTC.
    Producer chỉ cần put vào:
        video_queue.put((idx, frame_bgr))
    """

    def __init__(self, session_id: str, fps: int = 25):
        self.session_id = session_id
        self.fps = fps
        self.video_queue: Queue[VideoItem] = Queue(maxsize=fps * 5)  # ~5s @ 25fps
        self.pc: Optional[RTCPeerConnection] = None
        self._closed = False
        self._lock = threading.Lock()

    def close_queues(self):
        """Đánh dấu queue đã đóng, dừng nhận dữ liệu mới."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            # Không cần sentinel nếu track chỉ get; khi đóng PC sẽ dừng recv()


class WebRTCService:
    """Quản lý nhiều phiên WebRTC và truyền dữ liệu video."""

    def __init__(self):
        self.sessions: Dict[str, WebRTCSession] = {}

    def create_or_get_session(self, session_id: str, fps: int = 25) -> WebRTCSession:
        """Tạo mới hoặc lấy session theo session_id."""
        sess = self.get_session(session_id)
        if not sess:
            sess = WebRTCSession(session_id, fps)
            self.sessions[session_id] = sess
            logger.info(f"Created WebRTC session {session_id})")
        else:
            logger.info(f"Got WebRTC session {session_id})")
        return sess

    def get_session(self, session_id: str) -> Optional[WebRTCSession]:
        """Trả về session theo session_id nếu tồn tại."""
        return self.sessions.get(session_id)

    def get_producer_queues(self, session_id: str) -> Queue:
        """Lấy video_queue để producer put dữ liệu."""
        sess = self.get_session(session_id)
        if not sess:
            raise KeyError(f"Session {session_id} chưa tồn tại")
        return sess.video_queue

    def ensure_session(self, session_id: str):
        """Đảm bảo session tồn tại, nếu chưa có thì tạo mới."""
        self.create_or_get_session(session_id)

    async def create_answer(
        self, session_id: str, offer_sdp: str, offer_type: str, fps: int = 25
    ) -> RTCSessionDescription:
        """Tạo answer SDP cho client từ offer."""
        try:
            if not offer_sdp:
                raise ValueError("Missing offer SDP")
            if not offer_type:
                raise ValueError("Missing offer type")

            logger.info(f"offer_type='{offer_type}', sdp_len={len(offer_sdp)}")

            sess = self.create_or_get_session(session_id, fps)

            # Try creating a more basic PeerConnection configuration
            from aiortc import RTCConfiguration, RTCIceServer

            config = RTCConfiguration(
                iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
            )
            pc = RTCPeerConnection(configuration=config)
            sess.pc = pc

            @pc.on("connectionstatechange")
            async def _on_state():
                logger.info(f"PC {session_id} state={pc.connectionState}")
                if pc.connectionState in ("failed", "closed", "disconnected"):
                    await self.close(session_id)

            # Thêm track sử dụng queue
            video_track = VideoTrack(sess.video_queue, sess.fps)

            logger.info(f"Adding video track: {video_track}")
            pc.addTrack(video_track)

            logger.info(
                f"PC has {len(pc.getTransceivers())} transceivers after adding tracks"
            )

            @pc.on("track")
            def _on_track(track):
                logger.info(f"Client track received [kind={track.kind}] (ignored)")
                MediaBlackhole().addTrack(track)

            try:
                offer = RTCSessionDescription(sdp=offer_sdp, type=offer_type)
                logger.info(f"Created RTCSessionDescription successfully")
            except Exception as sdp_error:
                logger.error(f"RTCSessionDescription creation failed: {sdp_error}")
                raise ValueError(f"Invalid SDP or type: {sdp_error}")

            try:
                await pc.setRemoteDescription(offer)
                logger.info(f"setRemoteDescription successful")
            except Exception as set_error:
                logger.error(f"setRemoteDescription failed: {set_error}")
                raise ValueError(f"Failed to set remote description: {set_error}")

            try:
                answer = await pc.createAnswer()
                logger.info(f"createAnswer successful, answer type: {answer.type}")
            except Exception as answer_error:
                logger.error(f"createAnswer failed: {answer_error}")
                raise ValueError(f"Failed to create answer: {answer_error}")

            try:
                await pc.setLocalDescription(answer)
                logger.info(f"setLocalDescription successful")
            except Exception as local_error:
                logger.error(f"setLocalDescription failed: {local_error}")
                raise ValueError(f"Failed to set local description: {local_error}")

            try:
                local_desc = pc.localDescription
                logger.info(
                    f"Got localDescription: type={local_desc.type if local_desc else 'None'}"
                )
                return local_desc
            except Exception as desc_error:
                logger.error(f"Failed to get localDescription: {desc_error}")
                raise ValueError(f"Failed to get local description: {desc_error}")
        except Exception as e:
            logger.error(f"[create_answer] error: {e}")
            raise

    def push_video_frame(
        self,
        session_id: str,
        idx: int,
        frame_bgr: np.ndarray,
        drop_if_full: bool = True,
    ):
        """Đẩy frame video vào queue của session."""
        try:
            sess = self.sessions.get(session_id)
            if not sess:
                return
            q = sess.video_queue
            if drop_if_full and q.full():
                try:
                    q.get_nowait()
                except Empty:
                    pass
            q.put((idx, frame_bgr))
        except Exception as e:
            logger.error("push_video_frame error: %s", e)

    async def close(self, session_id: str):
        """Đóng session và giải phóng tài nguyên."""
        try:
            sess = self.sessions.pop(session_id, None)
            if not sess:
                return
            sess.close_queues()
            if sess.pc:
                await sess.pc.close()
            logger.info("Closed WebRTC session %s", session_id)
        except Exception as e:
            logger.error("close error: %s", e)


webrtc_service = WebRTCService()
