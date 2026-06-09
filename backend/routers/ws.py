import json
from fastapi import APIRouter, WebSocket, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db, AsyncSessionLocal
from backend.services.queue_service import QueueService
from backend.schemas import QueueEntry

router = APIRouter()

# Store active WebSocket connections
active_connections: list[WebSocket] = []


async def send_queue_to_all():
    """Broadcast current queue to all connected clients"""
    async with AsyncSessionLocal() as db:
        queue = await QueueService.get_full_queue(db)
        message = {
            "type": "queue_update",
            "queue": [entry.model_dump(mode="json") for entry in queue]
        }
        
        disconnected = []
        for connection in active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            if conn in active_connections:
                active_connections.remove(conn)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint: send queue on connect, broadcast on mutations"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send current queue on connect
        async with AsyncSessionLocal() as db:
            queue = await QueueService.get_full_queue(db)
            initial_message = {
                "type": "queue_update",
                "queue": [entry.model_dump(mode="json") for entry in queue]
            }
            await websocket.send_json(initial_message)
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)
