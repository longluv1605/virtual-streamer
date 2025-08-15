from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List
import json

from ..database import get_db, StreamSessionDatabaseService
from ..models import (
    StreamSessionCreate,
    StreamSessionResponse, 
    StreamProductResponse
)
from ..services import stream_processor
from ._manager import connection_manager

import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# Stream session endpoints
@router.post("", response_model=StreamSessionResponse)
async def create_session(session: StreamSessionCreate, db: Session = Depends(get_db)):
    return StreamSessionDatabaseService.create_session(db, session)


@router.get("", response_model=List[StreamSessionResponse])
async def get_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return StreamSessionDatabaseService.get_sessions(db, skip, limit)


@router.get("/{session_id}", response_model=StreamSessionResponse)
async def get_session(session_id: int, db: Session = Depends(get_db)):
    session = StreamSessionDatabaseService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/products", response_model=List[StreamProductResponse])
async def get_session_products(session_id: int, db: Session = Depends(get_db)):
    return StreamSessionDatabaseService.get_session_products(db, session_id)


@router.post("/{session_id}/prepare")
async def prepare_session(
    session_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """Prepare session by generating scripts, audio, and videos"""
    session = StreamSessionDatabaseService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "preparing":
        raise HTTPException(status_code=400, detail="Session is not in preparing state")

    # Update status to processing
    StreamSessionDatabaseService.update_session_status(db, session_id, "processing")

    # Process in background
    background_tasks.add_task(process_session_background, session_id)

    return {"message": "Session preparation started", "session_id": session_id}


async def process_session_background(session_id: int):
    """Background task to process session"""
    db = next(get_db())
    try:
        success = await stream_processor.process_session(session_id, db)
        if success:
            await connection_manager.broadcast(
                json.dumps(
                    {
                        "type": "session_ready",
                        "session_id": session_id,
                        "message": "Session preparation completed",
                    }
                )
            )
        else:
            await connection_manager.broadcast(
                json.dumps(
                    {
                        "type": "session_error",
                        "session_id": session_id,
                        "message": "Session preparation failed",
                    }
                )
            )
    except Exception as e:
        logger.error(f"Background processing error: {e}")
        StreamSessionDatabaseService.update_session_status(db, session_id, "error")
    finally:
        db.close()


@router.post("/{session_id}/start")
async def start_session(session_id: int, db: Session = Depends(get_db)):
    """Start live session"""
    session = StreamSessionDatabaseService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "ready":
        raise HTTPException(status_code=400, detail="Session is not ready")

    # Update status to live
    StreamSessionDatabaseService.update_session_status(db, session_id, "live")

    await connection_manager.broadcast(
        json.dumps(
            {
                "type": "session_started",
                "session_id": session_id,
                "message": "Live session started",
            }
        )
    )
    return {"message": "Session started", "session_id": session_id}


@router.post("/{session_id}/stop")
async def stop_session(session_id: int, db: Session = Depends(get_db)):
    """Stop live session"""
    session = StreamSessionDatabaseService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update status to completed
    StreamSessionDatabaseService.update_session_status(db, session_id, "completed")

    await connection_manager.broadcast(
        json.dumps(
            {
                "type": "session_stopped",
                "session_id": session_id,
                "message": "Live session stopped",
            }
        )
    )
    return {"message": "Session stopped", "session_id": session_id}
