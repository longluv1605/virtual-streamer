from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ._manager import connection_manager


router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            await connection_manager.send_personal_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
