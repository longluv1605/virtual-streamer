from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path

from src.api import register_routers
from src.database import (
    create_tables,
    get_db,
    init_sample_data,
)

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Virtual Streamer server...")

    # Initialize database
    db = next(get_db())
    init_sample_data(db)
    db.close()

    # Initialize MuseTalk models (optional, only if needed)
    try:
        from src.services.musetalk import initialize_musetalk_on_startup

        logger.info("Initializing MuseTalk models...")
        success = initialize_musetalk_on_startup()
        if success:
            logger.info("MuseTalk models loaded successfully")
        else:
            logger.warning("MuseTalk models failed to load - will use demo mode")
    except Exception as e:
        logger.error(f"MuseTalk initialization error: {e} - will use demo mode")

    logger.info("Server startup complete")
    yield
    # Shutdown (if needed)


# Create FastAPI app
app = FastAPI(title="Virtual Streamer API", version="1.0.0", lifespan=lifespan)
register_routers(app)

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

# Create output directories first with absolute paths
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
outputs_dir = os.path.join(current_dir, "outputs")
static_dir = os.path.join(current_dir, "static")

print(f"Current working directory: {os.getcwd()}")
print(f"Script directory: {current_dir}")
print(f"Outputs directory: {outputs_dir}")

Path(outputs_dir, "audio").mkdir(parents=True, exist_ok=True)
Path(outputs_dir, "videos").mkdir(parents=True, exist_ok=True)
Path(static_dir).mkdir(parents=True, exist_ok=True)

print(f"Created directories - outputs exists: {os.path.exists(outputs_dir)}")
print(f"Audio dir exists: {os.path.exists(os.path.join(outputs_dir, 'audio'))}")

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")


# Serve frontend
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse("static/index.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    return FileResponse("static/admin.html")


@app.get("/products", response_class=HTMLResponse)
async def products_page():
    return FileResponse("static/products.html")


@app.get("/live/{session_id:int}", response_class=HTMLResponse)
async def live_session(session_id: int):
    return FileResponse("static/live.html")


# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Virtual Streamer API is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="localhost", port=8000, reload=False)
