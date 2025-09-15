from fastapi import WebSocket
from typing import List

import asyncio
from starlette.websockets import WebSocketDisconnect

try:
    from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
except Exception:
    ConnectionClosedOK = ConnectionClosedError = Exception


import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s",
)
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Use a list for deterministic order; we'll remove safely
        self.active_connections: List[WebSocket] = []
        # Event loop reference set at FastAPI startup
        self.loop = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str) -> None:
        """Send message to all active websockets, remove clients that are closed."""
        if not getattr(self, "active_connections", None):
            return

        # copy to avoid mutation during iteration
        conns = list(self.active_connections)
        to_remove = []

        for ws in conns:
            try:
                await ws.send_text(message)
            except (
                ConnectionClosedOK,
                ConnectionClosedError,
                WebSocketDisconnect,
            ) as e:
                logger.info(f"Removing closed websocket during broadcast: {e}")
                to_remove.append(ws)
            except Exception as e:
                logger.error(
                    f"Unexpected error sending websocket message: {e}", exc_info=True
                )
                # remove on unexpected errors to avoid repeated failures
                to_remove.append(ws)

        for ws in to_remove:
            try:
                self.active_connections.remove(ws)
            except ValueError:
                pass


############################
connection_manager = ConnectionManager()
