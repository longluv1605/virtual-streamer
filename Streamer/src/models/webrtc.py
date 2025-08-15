from pydantic import BaseModel
from typing import Optional


class Offer(BaseModel):
    """
    Dữ liệu Offer mà client gửi lên khi muốn bắt đầu kết nối WebRTC.
    """
    session_id: Optional[str]
    sdp: Optional[str]
    type: Optional[str]
    fps: Optional[int] = 25
    sample_rate: Optional[int] = 16000