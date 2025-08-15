from sqlalchemy.orm import Session

from fastapi import APIRouter, HTTPException, Depends
from ..services import webrtc_service, stream_processor
from ..models import Offer
from ..database import get_db

router = APIRouter(prefix="/webrtc", tags=["webrtc"])

import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

@router.post("/offer")
async def create_offer(body: Offer):
    """
    Nhận Offer từ client, tạo Answer SDP để trả lại cho client.
    """
    try:
        # Debug: log what client sent
        logger.info(f"Received offer: session_id={body.session_id}, type={body.type}, sdp_len={len(body.sdp or '')}")
        
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
        logger.error(f"Invalid offer for session {body.session_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating offer for session {body.session_id}: {e}")
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
        logger.error("Error getting status for session %s", session_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/realtime/start")
async def start_realtime(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Start realtime session với MuseTalk support"""
    try:
        result = stream_processor.start_realtime_session(db, session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/avatar/prepare")
async def prepare_avatar(avatar_id: str, video_path: str):
    """Prepare avatar cho realtime streaming"""
    try:
        success = stream_processor.prepare_avatar_for_realtime(avatar_id, video_path)
        return {"status": "success" if success else "failed", "avatar_id": avatar_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/avatar/initialize")
async def initialize_musetalk():
    """Initialize MuseTalk models manually"""
    try:
        from src.services.musetalk import initialize_musetalk_on_startup
        success = initialize_musetalk_on_startup()
        return {"status": "success" if success else "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/musetalk/status")
async def musetalk_status():
    """Check MuseTalk service status"""
    try:
        from src.services.musetalk import get_musetalk_realtime_service
        service = get_musetalk_realtime_service()
        return {
            "initialized": service.is_ready(),
            "current_avatar": service.get_current_avatar(),
            "loaded_avatars": list(service._avatars.keys()) if service._avatar else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
