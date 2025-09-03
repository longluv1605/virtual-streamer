from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..services import ChatManager
from ..models import ChatConnectRequest

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
chat_manager = ChatManager()


@router.get("/platforms")
async def get_platforms():
    return {"platforms": chat_manager.get_supported_platforms()}

@router.post("/start")
async def start_chat(body: ChatConnectRequest):
    try:
        await validate_chat(body)
        await connect_chat(body)
        logger.info("Started chat...")
        return {"success": True}
    except HTTPException as e:
        # Cho phép FastAPI xử lý HTTPException
        raise e
    except Exception as e:
        logger.error(f"Starting chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# @router.post("/validate")
async def validate_chat(body: ChatConnectRequest):
    if body.platform not in chat_manager.get_supported_platforms():
        logger.error("Unsupported platform")
        raise HTTPException(status_code=400, detail="Unsupported platform")
    if not body.live_id or len(body.live_id) < 3:
        logger.error("Invalid live_id")
        raise HTTPException(status_code=400, detail="Invalid live_id")
    logger.info("Validate successfully...")
    return True

# @router.post("/connect")
async def connect_chat(body: ChatConnectRequest):
    if not chat_manager.set_platform(body.platform):
        logger.error("Cannot set platform")
        raise HTTPException(status_code=400, detail="Cannot set platform")
    ok = chat_manager.connect(body.live_id)
    if not ok:
        logger.error("Cannot connect to live")
        raise HTTPException(status_code=400, detail="Cannot connect to live")
    logger.info("Connect successfully...")
    return ok

@router.post("/disconnect")
async def disconnect_chat():
    ok = chat_manager.disconnect()
    return {"success": ok}

@router.get("/status")
async def chat_status():
    return {
        "platform": chat_manager.get_current_platform(),
        "connected": chat_manager.is_connected()
    }

@router.get("/comments")
async def get_comments():
    comments = chat_manager.get_new_comments()
    return {"comments": comments, "count": len(comments)}