from fastapi import APIRouter, HTTPException

from ..models import ChatValidateRequest

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s")
logger = logging.getLogger(__name__)


####################################
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/validate")
async def validate_chat(body: ChatValidateRequest):
    try:
        if body.live_id == 'ok':
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Validate chat error: {e}")
        raise HTTPException(status_code=400, detail=str(e))