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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Create output directories
Path("outputs/audio").mkdir(parents=True, exist_ok=True)
Path("outputs/videos").mkdir(parents=True, exist_ok=True)
Path("static").mkdir(parents=True, exist_ok=True)


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
