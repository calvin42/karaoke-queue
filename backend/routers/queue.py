from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.schemas import QueueEntryCreate, QueueEntry, QueueListResponse
from backend.services.queue_service import QueueService
from backend.routers.ws import send_queue_to_all

router = APIRouter()


@router.get("/queue", response_model=QueueListResponse)
async def get_queue(db: AsyncSession = Depends(get_db)):
    """Get full queue: singing first, then waiting by position, then done"""
    queue = await QueueService.get_full_queue(db)
    return QueueListResponse(queue=queue)


@router.post("/queue", response_model=QueueEntry, status_code=201)
async def add_to_queue(entry: QueueEntryCreate, db: AsyncSession = Depends(get_db)):
    """Add entry to queue. Auto-sing if no current singer."""
    new_entry = await QueueService.add_entry(db, entry.singer, entry.song)
    await send_queue_to_all()
    return new_entry


@router.post("/queue/next")
async def next_singer(db: AsyncSession = Depends(get_db)):
    """Mark current as done, promote next waiting to singing"""
    success = await QueueService.next_singer(db)
    if not success:
        raise HTTPException(status_code=400, detail="No current singer")
    await send_queue_to_all()
    return {"status": "ok"}


@router.patch("/queue/{entry_id}/move")
async def move_entry(entry_id: int, new_position: int, db: AsyncSession = Depends(get_db)):
    """Move waiting entry to new position"""
    result = await QueueService.move_waiting_entry(db, entry_id, new_position)
    if not result:
        raise HTTPException(status_code=400, detail="Cannot move singing or done entries")
    await send_queue_to_all()
    return result
