from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path
from contextlib import asynccontextmanager
from backend.database import init_db
from backend.routers import queue, ws
from backend.routers.ws import send_queue_to_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    await init_db()
    yield


app = FastAPI(title="Karaoke Queue", lifespan=lifespan)

# Include routers
app.include_router(queue.router)
app.include_router(ws.router)


@app.get("/")
async def root():
    """Serve frontend"""
    return FileResponse("frontend/index.html")


# Mount static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# Export send_queue_to_all for use in routers
app.send_queue_to_all = send_queue_to_all


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
