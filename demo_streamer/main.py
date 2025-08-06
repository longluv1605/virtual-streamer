from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    BackgroundTasks,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from contextlib import asynccontextmanager
import asyncio
import json
from pathlib import Path

from src.models import (
    create_tables,
    get_db,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    PaginatedProductResponse,
    # BulkProductUpdate,
    ProductStatsResponse,
    AvatarCreate,
    AvatarUpdate,
    AvatarResponse,
    StreamSessionCreate,
    StreamSessionResponse,
    StreamProductResponse,
    CommentCreate,
    CommentResponse,
    ScriptTemplateCreate,
    ScriptTemplateResponse,
)
from src.database import (
    ProductService,
    StreamSessionService,
    CommentService,
    ScriptTemplateService,
    init_sample_data,
)
from src.services import StreamProcessor, AvatarService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db = next(get_db())
    init_sample_data(db)
    db.close()
    yield
    # Shutdown (if needed)


# Create FastAPI app
app = FastAPI(title="Virtual Streamer API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables and initialize data
create_tables()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Create output directories
Path("outputs/audio").mkdir(parents=True, exist_ok=True)
Path("outputs/videos").mkdir(parents=True, exist_ok=True)
Path("static").mkdir(parents=True, exist_ok=True)

# Global stream processor
stream_processor = StreamProcessor()


# WebSocket manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass


manager = ConnectionManager()


# Product endpoints
@app.get("/api/products/categories")
async def get_categories(db: Session = Depends(get_db)):
    """Get list of all product categories"""
    categories = ProductService.get_categories(db)
    return categories


@app.get("/api/products/stats/summary", response_model=ProductStatsResponse)
async def get_product_stats(db: Session = Depends(get_db)):
    """Get product statistics summary"""
    stats = ProductService.get_product_stats(db)
    return stats


# @app.post("/api/products/bulk")
# async def create_products_bulk(
#     products: List[ProductCreate], db: Session = Depends(get_db)
# ):
#     """Create multiple products at once"""
#     created_products = ProductService.create_products_bulk(db, products)
#     return {
#         "message": f"Created {len(created_products)} products successfully",
#         "products": created_products,
#     }


# @app.put("/api/products/bulk/update")
# async def update_products_bulk(
#     updates: List[BulkProductUpdate], db: Session = Depends(get_db)
# ):
#     """Update multiple products at once"""
#     # Convert to dict format expected by service
#     update_dicts = []
#     for update in updates:
#         update_dict = {"id": update.id}
#         for field, value in update.dict().items():
#             if field != "id" and value is not None:
#                 update_dict[field] = value
#         update_dicts.append(update_dict)

#     updated_count = ProductService.update_products_bulk(db, update_dicts)
#     return {"message": f"Updated {updated_count} products successfully"}


@app.post("/api/products", response_model=ProductResponse)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product"""
    return ProductService.create_product(db, product)


@app.get("/api/products", response_model=PaginatedProductResponse)
async def get_products(
    page: int = 1,
    limit: int = 100,
    active_only: bool = True,
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    """Get products with filtering options"""
    skip = (page - 1) * limit
    actual_active_only = active_only and not include_inactive

    products = ProductService.get_products(
        db=db,
        skip=skip,
        limit=limit,
        active_only=actual_active_only,
        category=category,
        search=search,
        min_price=min_price,
        max_price=max_price,
    )

    total = ProductService.count_products(
        db=db,
        active_only=actual_active_only,
        category=category,
        search=search,
        min_price=min_price,
        max_price=max_price,
    )

    pages = (total + limit - 1) // limit

    return PaginatedProductResponse(
        items=products, total=total, page=page, pages=pages, limit=limit
    )


@app.get("/api/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID"""
    product = ProductService.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.put("/api/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int, product_update: ProductCreate, db: Session = Depends(get_db)
):
    """Update a product completely"""
    product = ProductService.update_product(db, product_id, product_update.dict())
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.patch("/api/products/{product_id}", response_model=ProductResponse)
async def patch_product(
    product_id: int, product_update: ProductUpdate, db: Session = Depends(get_db)
):
    """Partially update a product"""
    # Only include non-None fields in the update
    update_data = {k: v for k, v in product_update.dict().items() if v is not None}
    product = ProductService.update_product(db, product_id, update_data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.delete("/api/products/{product_id}")
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Soft delete a product (mark as inactive)"""
    success = ProductService.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}


@app.put("/api/products/{product_id}/restore")
async def restore_product(product_id: int, db: Session = Depends(get_db)):
    """Restore a soft-deleted product"""
    product = ProductService.restore_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product restored successfully", "product": product}


@app.delete("/api/products/{product_id}/hard")
async def hard_delete_product(product_id: int, db: Session = Depends(get_db)):
    """Permanently delete a product from database"""
    success = ProductService.hard_delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product permanently deleted"}


# Stream session endpoints
@app.post("/api/sessions", response_model=StreamSessionResponse)
async def create_session(session: StreamSessionCreate, db: Session = Depends(get_db)):
    print("hiihihih")
    return StreamSessionService.create_session(db, session)


@app.get("/api/sessions", response_model=List[StreamSessionResponse])
async def get_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return StreamSessionService.get_sessions(db, skip, limit)


@app.get("/api/sessions/{session_id}", response_model=StreamSessionResponse)
async def get_session(session_id: int, db: Session = Depends(get_db)):
    session = StreamSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get(
    "/api/sessions/{session_id}/products", response_model=List[StreamProductResponse]
)
async def get_session_products(session_id: int, db: Session = Depends(get_db)):
    return StreamSessionService.get_session_products(db, session_id)


@app.post("/api/sessions/{session_id}/prepare")
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


@app.post("/api/sessions/{session_id}/start")
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


@app.post("/api/sessions/{session_id}/stop")
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


# Comment endpoints
@app.post("/api/sessions/{session_id}/comments", response_model=CommentResponse)
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


@app.get("/api/sessions/{session_id}/comments", response_model=List[CommentResponse])
async def get_session_comments(
    session_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    return CommentService.get_session_comments(db, session_id, skip, limit)


@app.get("/api/sessions/{session_id}/questions", response_model=List[CommentResponse])
async def get_unanswered_questions(session_id: int, db: Session = Depends(get_db)):
    return CommentService.get_unanswered_questions(db, session_id)


@app.post("/api/sessions/{session_id}/auto-answer-question/{comment_id}")
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


@app.put("/api/comments/{comment_id}/answer")
async def mark_comment_answered(comment_id: int, db: Session = Depends(get_db)):
    comment = CommentService.mark_comment_answered(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"message": "Comment marked as answered"}


# Q&A endpoints for live sessions
@app.post("/api/sessions/{session_id}/answer-question/{comment_id}")
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


@app.get("/api/sessions/{session_id}/questions/unanswered")
async def get_session_unanswered_questions(
    session_id: int, db: Session = Depends(get_db)
):
    """Get unanswered questions for live session management"""
    return await stream_processor.get_unanswered_questions(session_id, db)



# Script template endpoints
@app.post("/api/templates", response_model=ScriptTemplateResponse)
async def create_template(
    template: ScriptTemplateCreate, db: Session = Depends(get_db)
):
    return ScriptTemplateService.create_template(db, template)


@app.get("/api/templates", response_model=List[ScriptTemplateResponse])
async def get_templates(category: Optional[str] = None, db: Session = Depends(get_db)):
    return ScriptTemplateService.get_templates(db, category)


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            await manager.send_personal_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Serve frontend
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse("static/index.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    return FileResponse("static/admin.html")


@app.get("/live/{session_id:int}", response_class=HTMLResponse)
async def live_session(session_id: int):
    return FileResponse("static/live.html")


@app.get("/products", response_class=HTMLResponse)
async def products_page():
    return FileResponse("static/products.html")


# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Virtual Streamer API is running"}


# Avatar endpoints
@app.get("/api/avatars")
async def get_available_avatars():
    """Get list of available avatar videos from both local and MuseTalk directories"""
    avatar_files = []
    video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    image_extensions = {".png", ".jpg", ".jpeg"}

    # 1. Check local avatars directory
    local_avatars_dir = Path("static/avatars")
    local_avatars_dir.mkdir(exist_ok=True)

    for file_path in local_avatars_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            avatar_files.append(
                {
                    "name": f"Local: {file_path.stem}",
                    "filename": file_path.name,
                    "path": f"/static/avatars/{file_path.name}",
                    "size": file_path.stat().st_size,
                    "source": "local",
                    "type": "video",
                }
            )

    # 2. Check MuseTalk video avatars directory
    musetalk_video_dir = Path("../MuseTalk/data/video")
    if musetalk_video_dir.exists():
        for file_path in musetalk_video_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                # Use relative path for easier handling
                relative_path = f"../MuseTalk/data/video/{file_path.name}"
                avatar_files.append(
                    {
                        "name": f"MuseTalk Video: {file_path.stem}",
                        "filename": file_path.name,
                        "path": relative_path,
                        "size": file_path.stat().st_size,
                        "source": "musetalk_video",
                        "type": "video",
                    }
                )

    # 3. Check MuseTalk demo images (can be used for image-based avatars)
    musetalk_demo_dir = Path("../MuseTalk/assets/demo")
    if musetalk_demo_dir.exists():
        for demo_folder in musetalk_demo_dir.iterdir():
            if demo_folder.is_dir():
                # Look for image files in each demo folder
                for file_path in demo_folder.iterdir():
                    if (
                        file_path.is_file()
                        and file_path.suffix.lower() in image_extensions
                    ):
                        # Use relative path for easier handling
                        relative_path = f"../MuseTalk/assets/demo/{demo_folder.name}/{file_path.name}"
                        avatar_files.append(
                            {
                                "name": f"MuseTalk Demo: {demo_folder.name}",
                                "filename": file_path.name,
                                "path": relative_path,
                                "size": file_path.stat().st_size,
                                "source": "musetalk_demo",
                                "type": "image",
                            }
                        )
                        break  # Only take one image per demo folder

    # Sort by source type and name
    avatar_files.sort(key=lambda x: (x["source"], x["name"]))

    return {"avatars": avatar_files}


@app.post("/api/avatars/upload")
async def upload_avatar(file: UploadFile = File(...)):
    """Upload avatar video file"""
    # Validate file type
    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".webm")):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only video files are allowed."
        )

    # Create avatars directory if it doesn't exist
    avatars_dir = Path("static/avatars")
    avatars_dir.mkdir(exist_ok=True)

    # Save file
    file_path = avatars_dir / file.filename
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return {
        "message": "Avatar uploaded successfully",
        "filename": file.filename,
        "path": f"/static/avatars/{file.filename}",
    }


# ===== AVATAR MANAGEMENT ENDPOINTS =====


@app.get("/api/avatars/database", response_model=List[AvatarResponse])
async def list_database_avatars(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """List all avatars in database"""
    try:
        avatars = AvatarService.list_avatars(db, skip=skip, limit=limit)
        return avatars
    except Exception as e:
        print(f"Error listing avatars: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/avatars/database", response_model=AvatarResponse)
async def create_avatar(avatar_data: AvatarCreate, db: Session = Depends(get_db)):
    """Create or get existing avatar"""
    try:
        avatar = AvatarService.get_or_create_avatar(
            db, video_path=avatar_data.video_path, name=avatar_data.name
        )
        # Update bbox_shift if provided
        if avatar_data.bbox_shift != 0:
            avatar.bbox_shift = avatar_data.bbox_shift
            db.commit()
            db.refresh(avatar)

        return avatar
    except Exception as e:
        print(f"Error creating avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/avatars/database/{avatar_id}", response_model=AvatarResponse)
async def get_avatar(avatar_id: int, db: Session = Depends(get_db)):
    """Get avatar by ID"""
    avatar = AvatarService.get_avatar_by_id(db, avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return avatar


@app.put("/api/avatars/database/{avatar_id}", response_model=AvatarResponse)
async def update_avatar(
    avatar_id: int, avatar_update: AvatarUpdate, db: Session = Depends(get_db)
):
    """Update avatar"""
    try:
        avatar = AvatarService.get_avatar_by_id(db, avatar_id)
        if not avatar:
            raise HTTPException(status_code=404, detail="Avatar not found")

        # Update fields
        if avatar_update.name:
            avatar.name = avatar_update.name
        if avatar_update.bbox_shift is not None:
            avatar.bbox_shift = avatar_update.bbox_shift
        if avatar_update.is_prepared is not None:
            avatar.is_prepared = avatar_update.is_prepared
        if avatar_update.preparation_status:
            avatar.preparation_status = avatar_update.preparation_status

        db.commit()
        db.refresh(avatar)
        return avatar
    except Exception as e:
        print(f"Error updating avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/avatars/database/{avatar_id}/prepare")
async def prepare_avatar(
    avatar_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """Prepare avatar for MuseTalk"""
    try:
        avatar = AvatarService.get_avatar_by_id(db, avatar_id)
        if not avatar:
            raise HTTPException(status_code=404, detail="Avatar not found")

        if avatar.is_prepared:
            return {"message": "Avatar already prepared", "avatar_id": avatar_id}

        # Start background preparation
        AvatarService.update_avatar_preparation_status(db, avatar_id, "processing")

        # TODO: Add actual preparation logic here
        # For now, just mark as prepared
        background_tasks.add_task(_prepare_avatar_background, avatar_id)

        return {"message": "Avatar preparation started", "avatar_id": avatar_id}

    except Exception as e:
        print(f"Error preparing avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _prepare_avatar_background(avatar_id: int):
    """Background task to prepare avatar"""
    try:
        # Get database session
        from src.models import SessionLocal

        db = SessionLocal()

        try:
            # Update status to processing
            AvatarService.update_avatar_preparation_status(db, avatar_id, "processing")

            # TODO: Add actual MuseTalk preparation logic here
            # For now, just simulate preparation
            await asyncio.sleep(5)  # Simulate processing time

            # Mark as prepared
            AvatarService.update_avatar_preparation_status(
                db, avatar_id, "completed", is_prepared=True
            )

            print(f"Avatar {avatar_id} preparation completed")

        finally:
            db.close()

    except Exception as e:
        print(f"Error in background avatar preparation: {e}")
        # Mark as error if failed
        try:
            from src.models import SessionLocal

            db = SessionLocal()
            AvatarService.update_avatar_preparation_status(db, avatar_id, "error")
            db.close()
        except:
            pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
