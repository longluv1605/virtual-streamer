import asyncio
import fractions
import threading
from queue import Queue, Empty
from typing import Dict, Optional, Tuple

import numpy as np
from av import VideoFrame, AudioFrame
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    MediaStreamTrack,
)
from aiortc.contrib.media import MediaBlackhole


VideoItem = Tuple[int, np.ndarray]  # (frame_idx, bgr_frame[h,w,3])
AudioItem = Tuple[int, np.ndarray]  # (frame_idx, mono_samples float32|int16)


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
            print("VideoTrack recv error: %s", e)
            raise


class AudioTrack(MediaStreamTrack):
    """Audio track lấy audio chunk từ Queue để gửi qua WebRTC."""

    kind = "audio"

    def __init__(self, queue: Queue, sample_rate: int):
        super().__init__()
        self._queue = queue
        self._sr = sample_rate
        self._loop = asyncio.get_running_loop()
        self._pts_samples = 0  # tích lũy mẫu đã gửi

    async def recv(self) -> AudioFrame:
        """Nhận audio chunk từ Queue và trả về AudioFrame."""
        try:
            item: AudioItem = await self._loop.run_in_executor(None, self._queue.get)
            _idx, samples = item

            if samples.dtype == np.int16:
                fmt = "s16"
            else:
                if samples.dtype != np.float32:
                    samples = samples.astype(np.float32)
                fmt = "flt"

            n = samples.shape[0]
            af = AudioFrame.from_ndarray(
                samples.reshape(1, n), format=fmt, layout="mono"
            )
            af.sample_rate = self._sr
            af.time_base = fractions.Fraction(1, self._sr)
            af.pts = self._pts_samples
            self._pts_samples += n
            return af
        except Exception as e:
            print("AudioTrack recv error: %s", e)
            raise


class WebRTCSession:
    """
    Lưu trữ queue và PeerConnection cho một phiên WebRTC.
    Producer chỉ cần put vào:
        video_queue.put((idx, frame_bgr))
        audio_queue.put((idx, audio_chunk))
    """

    def __init__(self, session_id: str, fps: int, sample_rate: int):
        self.session_id = session_id
        self.fps = fps
        self.sample_rate = sample_rate
        self.video_queue: Queue[VideoItem] = Queue(maxsize=120)  # ~5s @ 25fps
        self.audio_queue: Queue[AudioItem] = Queue(maxsize=5000)  # tùy chunk size
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
    """Quản lý nhiều phiên WebRTC và truyền dữ liệu video/audio."""

    def __init__(self):
        self.sessions: Dict[str, WebRTCSession] = {}

    def create_or_get_session(
        self, session_id: str, fps: int, sample_rate: int
    ) -> WebRTCSession:
        """Tạo mới hoặc lấy session theo session_id."""
        sess = self.sessions.get(session_id)
        if not sess:
            sess = WebRTCSession(session_id, fps, sample_rate)
            self.sessions[session_id] = sess
            print(f"Created WebRTC session {session_id} (fps={fps}, sr={sample_rate})")
        else:
            print(f"Got WebRTC session {session_id} (fps={fps}, sr={sample_rate})")
        return sess

    def get_session(self, session_id: str) -> Optional[WebRTCSession]:
        """Trả về session theo session_id nếu tồn tại."""
        return self.sessions.get(session_id)

    def get_producer_queues(self, session_id: str) -> Tuple[Queue, Queue]:
        """Lấy (video_queue, audio_queue) để producer put dữ liệu."""
        sess = self.sessions.get(session_id)
        if not sess:
            raise KeyError(f"Session {session_id} chưa tồn tại")
        return sess.video_queue, sess.audio_queue

    def ensure_session(self, session_id: str, fps: int, sample_rate: int):
        """Đảm bảo session tồn tại, nếu chưa có thì tạo mới."""
        self.create_or_get_session(session_id, fps, sample_rate)

    async def create_answer(
        self,
        session_id: str,
        offer_sdp: str,
        offer_type: str,
        fps: int,
        sample_rate: int,
    ) -> RTCSessionDescription:
        """Tạo answer SDP cho client từ offer."""
        try:
            if not offer_sdp:
                raise ValueError("Missing offer SDP")
            if not offer_type:
                raise ValueError("Missing offer type")

            print(
                f"[DEBUG] offer_type='{offer_type}', sdp_len={len(offer_sdp)}"
            )

            sess = self.create_or_get_session(session_id, fps, sample_rate)

            # Try creating a more basic PeerConnection configuration
            from aiortc import RTCConfiguration, RTCIceServer

            config = RTCConfiguration(
                iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
            )
            pc = RTCPeerConnection(configuration=config)
            sess.pc = pc

            @pc.on("connectionstatechange")
            async def _on_state():
                print(f"PC {session_id} state={pc.connectionState}")
                if pc.connectionState in ("failed", "closed", "disconnected"):
                    await self.close(session_id)

            # Thêm track sử dụng queue
            video_track = VideoTrack(sess.video_queue, sess.fps)
            audio_track = AudioTrack(sess.audio_queue, sess.sample_rate)
            
            print(f"[DEBUG] Adding video track: {video_track}")
            pc.addTrack(video_track)
            print(f"[DEBUG] Adding audio track: {audio_track}")
            pc.addTrack(audio_track)
            
            print(f"[DEBUG] PC has {len(pc.getTransceivers())} transceivers after adding tracks")

            @pc.on("track")
            def _on_track(track):
                print(f"Client track received [kind={track.kind}] (ignored)")
                MediaBlackhole().addTrack(track)

            try:
                offer = RTCSessionDescription(sdp=offer_sdp, type=offer_type)
                print(f"[DEBUG] Created RTCSessionDescription successfully")
            except Exception as sdp_error:
                print(f"[DEBUG] RTCSessionDescription creation failed: {sdp_error}")
                raise ValueError(f"Invalid SDP or type: {sdp_error}")

            try:
                await pc.setRemoteDescription(offer)
                print(f"[DEBUG] setRemoteDescription successful")
            except Exception as set_error:
                print(f"[DEBUG] setRemoteDescription failed: {set_error}")
                raise ValueError(f"Failed to set remote description: {set_error}")

            try:
                answer = await pc.createAnswer()
                print(f"[DEBUG] createAnswer successful, answer type: {answer.type}")
            except Exception as answer_error:
                print(f"[DEBUG] createAnswer failed: {answer_error}")
                raise ValueError(f"Failed to create answer: {answer_error}")

            try:
                await pc.setLocalDescription(answer)
                print(f"[DEBUG] setLocalDescription successful")
            except Exception as local_error:
                print(f"[DEBUG] setLocalDescription failed: {local_error}")
                raise ValueError(f"Failed to set local description: {local_error}")

            try:
                local_desc = pc.localDescription
                print(
                    f"[DEBUG] Got localDescription: type={local_desc.type if local_desc else 'None'}"
                )
                return local_desc
            except Exception as desc_error:
                print(f"[DEBUG] Failed to get localDescription: {desc_error}")
                raise ValueError(f"Failed to get local description: {desc_error}")
        except Exception as e:
            print(f"[create_answer] error: {e}")
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
            print("push_video_frame error: %s", e)

    def push_audio_chunk(
        self,
        session_id: str,
        idx: int,
        audio_chunk: np.ndarray,
        drop_if_full: bool = False,
    ):
        """Đẩy audio chunk vào queue của session."""
        try:
            sess = self.sessions.get(session_id)
            if not sess:
                return
            q = sess.audio_queue
            if drop_if_full and q.full():
                try:
                    q.get_nowait()
                except Empty:
                    pass
            q.put((idx, audio_chunk))
        except Exception as e:
            print("push_audio_chunk error: %s", e)

    async def close(self, session_id: str):
        """Đóng session và giải phóng tài nguyên."""
        try:
            sess = self.sessions.pop(session_id, None)
            if not sess:
                return
            sess.close_queues()
            if sess.pc:
                await sess.pc.close()
            print("Closed WebRTC session %s", session_id)
        except Exception as e:
            print("close error: %s", e)


webrtc_service = WebRTCService()
