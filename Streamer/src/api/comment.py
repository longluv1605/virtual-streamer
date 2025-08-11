from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Optional
from pathlib import Path
import json

from ..database import get_db, StreamSessionService, CommentService
from ..models import (
    CommentCreate,
    CommentResponse,
)
from ._manager_ import stream_processor, manager

####################################
router = APIRouter(prefix="/sessions/{session_id}/comments", tags=["comments"])


# Comment endpoints
@router.post("", response_model=CommentResponse)
async def create_comment(
    session_id: int, comment: CommentCreate, db: Session = Depends(get_db)
):
    db_comment = CommentService.create_comment(db, session_id, comment)

    # Broadcast new comment to all connected clients
    await manager.broadcast(
        json.dumps(
            {
                "type": "new_comment",
                "session_id": session_id,
                "comment": {
                    "id": db_comment.id,
                    "username": db_comment.username,
                    "message": db_comment.message,
                    "is_question": db_comment.is_question,
                    "answered": db_comment.answered,
                    "answer_video_path": db_comment.answer_video_path,
                    "timestamp": db_comment.timestamp.isoformat(),
                },
            }
        )
    )
    return db_comment


@router.get("", response_model=List[CommentResponse])
async def get_session_comments(
    session_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    return CommentService.get_session_comments(db, session_id, skip, limit)


@router.get("/questions", response_model=List[CommentResponse])
async def get_unanswered_questions(session_id: int, db: Session = Depends(get_db)):
    return CommentService.get_unanswered_questions(db, session_id)


@router.post("/auto-answer-question/{comment_id}")
async def auto_answer_question(
    session_id: int,
    comment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Auto-generate answer video for a question when product video ends"""

    # Verify session exists and is live
    session = StreamSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "live":
        raise HTTPException(status_code=400, detail="Session is not live")

    # Verify comment exists and is a question
    comment = CommentService.get_session_comments(db, session_id, skip=0, limit=1000)
    target_comment = next((c for c in comment if c.id == comment_id), None)

    if not target_comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if not target_comment.is_question:
        raise HTTPException(
            status_code=400, detail="Comment is not marked as a question"
        )

    if target_comment.answered:
        return {"message": "Question already answered", "comment_id": comment_id}

    # Process Q&A in background
    background_tasks.add_task(
        process_qa_background, session_id, comment_id, target_comment.message, None
    )

    return {
        "message": "Auto answer generation started",
        "session_id": session_id,
        "comment_id": comment_id,
    }


@router.put("/{comment_id}/answer")
async def mark_comment_answered(comment_id: int, db: Session = Depends(get_db)):
    comment = CommentService.mark_comment_answered(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"message": "Comment marked as answered"}


# Q&A endpoints for live sessions
@router.post("/answer-question/{comment_id}")
async def answer_question(
    session_id: int,
    comment_id: int,
    background_tasks: BackgroundTasks,
    context: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Generate answer video for a question during live session"""

    # Verify session exists and is live
    session = StreamSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "live":
        raise HTTPException(status_code=400, detail="Session is not live")

    # Verify comment exists and is a question
    comment = CommentService.get_session_comments(db, session_id, skip=0, limit=1000)
    target_comment = next((c for c in comment if c.id == comment_id), None)

    if not target_comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if not target_comment.is_question:
        raise HTTPException(
            status_code=400, detail="Comment is not marked as a question"
        )

    if target_comment.answered:
        raise HTTPException(status_code=400, detail="Question already answered")

    # Process Q&A in background
    background_tasks.add_task(
        process_qa_background, session_id, comment_id, target_comment.message, context
    )

    await manager.broadcast(
        json.dumps(
            {
                "type": "question_processing",
                "session_id": session_id,
                "comment_id": comment_id,
                "message": f"Đang tạo video trả lời cho câu hỏi từ {target_comment.username}...",
            }
        )
    )

    return {
        "message": "Question answer generation started ",
        "session_id": session_id,
        "comment_id": comment_id,
    }


async def process_qa_background(
    session_id: int, comment_id: int, question: str, context: str = None
):
    """Background task to process Q&A"""
    db = next(get_db())
    try:
        video_path = await stream_processor.process_question_answer(
            session_id, comment_id, question, db, context
        )

        if video_path:
            # Broadcast success
            await manager.broadcast(
                json.dumps(
                    {
                        "type": "question_answered",
                        "session_id": session_id,
                        "comment_id": comment_id,
                        "video_path": video_path,
                        "message": "Đã tạo xong video trả lời câu hỏi!",
                    }
                )
            )
        else:
            # Broadcast error
            await manager.broadcast(
                json.dumps(
                    {
                        "type": "question_error",
                        "session_id": session_id,
                        "comment_id": comment_id,
                        "message": "Không thể tạo video trả lời câu hỏi",
                    }
                )
            )

    except Exception as e:
        print(f"Background Q&A processing error: {e}")
        # Broadcast error
        await manager.broadcast(
            json.dumps(
                {
                    "type": "question_error",
                    "session_id": session_id,
                    "comment_id": comment_id,
                    "message": f"Lỗi xử lý câu hỏi: {str(e)}",
                }
            )
        )
    finally:
        db.close()


@router.get("/questions/unanswered")
async def get_session_unanswered_questions(
    session_id: int, db: Session = Depends(get_db)
):
    """Get unanswered questions for live session management"""
    return await stream_processor.get_unanswered_questions(session_id, db)

