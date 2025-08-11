from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List
import json

from ..database import get_db, StreamSessionService
from ..models import (
    StreamSessionCreate,
    StreamSessionResponse, 
    StreamProductResponse
)
from ._manager_ import stream_processor, manager



router = APIRouter(prefix="/sessions", tags=["sessions"])


# Stream session endpoints
@router.post("", response_model=StreamSessionResponse)
async def create_session(session: StreamSessionCreate, db: Session = Depends(get_db)):
    return StreamSessionService.create_session(db, session)


@router.get("", response_model=List[StreamSessionResponse])
async def get_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return StreamSessionService.get_sessions(db, skip, limit)


@router.get("/{session_id}", response_model=StreamSessionResponse)
async def get_session(session_id: int, db: Session = Depends(get_db)):
    session = StreamSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get(
    "/{session_id}/products", response_model=List[StreamProductResponse]
)
async def get_session_products(session_id: int, db: Session = Depends(get_db)):
    return StreamSessionService.get_session_products(db, session_id)


@router.post("/{session_id}/prepare")
async def prepare_session(
    session_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """Prepare session by generating scripts, audio, and videos"""
    session = StreamSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "preparing":
        raise HTTPException(status_code=400, detail="Session is not in preparing state")

    # Update status to processing
    StreamSessionService.update_session_status(db, session_id, "processing")

    # Process in background
    background_tasks.add_task(process_session_background, session_id)

    return {"message": "Session preparation started", "session_id": session_id}


async def process_session_background(session_id: int):
    """Background task to process session"""
    db = next(get_db())
    try:
        success = await stream_processor.process_session(session_id, db)
        if success:
            await manager.broadcast(
                json.dumps(
                    {
                        "type": "session_ready",
                        "session_id": session_id,
                        "message": "Session preparation completed",
                    }
                )
            )
        else:
            await manager.broadcast(
                json.dumps(
                    {
                        "type": "session_error",
                        "session_id": session_id,
                        "message": "Session preparation failed",
                    }
                )
            )
    except Exception as e:
        print(f"Background processing error: {e}")
        StreamSessionService.update_session_status(db, session_id, "error")
    finally:
        db.close()


@router.post("/{session_id}/start")
async def start_session(session_id: int, db: Session = Depends(get_db)):
    """Start live session"""
    session = StreamSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "ready":
        raise HTTPException(status_code=400, detail="Session is not ready")

    # Update status to live
    StreamSessionService.update_session_status(db, session_id, "live")

    await manager.broadcast(
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
    session = StreamSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update status to completed
    StreamSessionService.update_session_status(db, session_id, "completed")

    await manager.broadcast(
        json.dumps(
            {
                "type": "session_stopped",
                "session_id": session_id,
                "message": "Live session stopped",
            }
        )
    )
    return {"message": "Session stopped", "session_id": session_id}

