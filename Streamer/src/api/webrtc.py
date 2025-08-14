from fastapi import APIRouter, HTTPException
from ..services import webrtc_service, stream_processor
from ..models import Offer

router = APIRouter(prefix="/webrtc", tags=["webrtc"])


@router.post("/offer")
async def create_offer(body: Offer):
    """
    Nhận Offer từ client, tạo Answer SDP để trả lại cho client.
    """
    try:
        # Debug: log what client sent
        print(f"[DEBUG] Received offer: session_id={body.session_id}, type={body.type}, sdp_len={len(body.sdp or '')}")
        
        # Chuẩn hóa type (một số client có thể không gửi hoặc gửi in hoa)
        offer_type = (body.type or "offer").lower()
        if offer_type != "offer":
            raise ValueError(f"Unsupported SDP type: {offer_type}")
        if not body.sdp:
            raise ValueError("Missing SDP string")
        if not body.session_id:
            raise ValueError("Missing session_id")
        
        answer = await webrtc_service.create_answer(
            session_id=body.session_id,
            offer_sdp=body.sdp,
            offer_type=body.type,
            fps=body.fps or 25,
            sample_rate=body.sample_rate or 16000,
        )
        return {"sdp": answer.sdp, "type": answer.type}
    except ValueError as e:
        print(f"Invalid offer for session {body.session_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error creating offer for session {body.session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status/{session_id}")
def status(session_id: str):
    """
    Lấy trạng thái của một session WebRTC.
    """
    try:
        sess = webrtc_service.get_session(session_id)
        if not sess:
            return {"exists": False}
        return {
            "exists": True,
            "fps": sess.fps,
            "sample_rate": sess.sample_rate,
            "video_queue": sess.video_queue.qsize(),
            "audio_queue": sess.audio_queue.qsize(),
        }
    except Exception as e:
        print("Error getting status for session %s", session_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/realtime/start")
async def start_realtime(session_id: str, fps: int = 25, sample_rate: int = 16000):
    # Hàm dưới là sync, trả về dict; nếu đổi thành async sau này cần await.
    try:
        result = stream_processor.start_realtime_session(
            session_id, fps=fps, sample_rate=sample_rate
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
