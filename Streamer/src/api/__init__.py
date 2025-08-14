from fastapi import FastAPI
from .session import router as session_router
from .product import router as product_router
from .comment import router as comment_router
from .avatar import router as avatar_router
from .template import router as template_router
from .websocket import router as websocket_router
from .webrtc import router as webrtc_router

def register_routers(app: FastAPI, api_prefix: str = "/api"):
    app.include_router(session_router, prefix=api_prefix)
    app.include_router(product_router, prefix=api_prefix)
    app.include_router(comment_router, prefix=api_prefix)
    app.include_router(avatar_router, prefix=api_prefix)
    app.include_router(template_router, prefix=api_prefix)
    app.include_router(websocket_router, prefix="")
    app.include_router(webrtc_router, prefix=api_prefix)