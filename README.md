# Karaoke Queue

A full-stack real-time karaoke queue web app for smartphone use.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLite (SQLAlchemy + aiosqlite), WebSockets
- **Frontend**: Single HTML file + CSS + vanilla JS
- **Tests**: pytest + pytest-asyncio + httpx

## Features

- Real-time queue updates via WebSocket
- Drag-and-drop reordering (for waiting entries)
- Dark/light mode toggle
- Web Notifications API integration
- Mobile-first responsive design (375px)
- Auto-reconnect WebSocket on disconnect

## Project Structure

```
karaoke-queue/
├── backend/
│   ├── main.py           # FastAPI app entry point
│   ├── models.py         # SQLAlchemy models
│   ├── database.py       # Database initialization
│   ├── schemas.py        # Pydantic schemas
│   ├── routers/
│   │   ├── queue.py      # Queue HTTP endpoints
│   │   └── ws.py         # WebSocket endpoint
│   ├── services/
│   │   └── queue_service.py  # Business logic
│   └── tests/
│       └── test_queue.py # Test suite
├── frontend/
│   ├── index.html        # Main HTML
│   ├── style.css         # Styles
│   └── app.js            # Client JS
├── requirements.txt      # Python dependencies
└── Dockerfile           # Container configuration
```

## Installation

```bash
pip install -r requirements.txt
```

## Running Locally

```bash
uvicorn backend.main:app --reload
```

Visit `http://localhost:8000`

## Running Tests

```bash
pytest backend/tests/test_queue.py -v
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/queue` | Get full queue (singing, waiting, done) |
| POST | `/queue` | Add entry to queue |
| POST | `/queue/next` | Mark singing as done, promote next waiting |
| PATCH | `/queue/{id}/move` | Move waiting entry to new position |
| WS | `/ws` | WebSocket for real-time updates |

## Deployment

### Render.com

1. Set build command: `pip install -r requirements.txt`
2. Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. Add Persistent Disk at `/data`
4. Set environment variable: `DATABASE_URL=sqlite+aiosqlite:////data/karaoke.db`

## Data Model

**Table: queue**
- `id` (int, primary key)
- `singer` (str)
- `song` (str)
- `status` (enum: waiting/singing/done)
- `position` (int)
- `created_at` (datetime)

## Rules

- Only one `singing` entry at a time
- `done` entries are immutable
- `singing` entries cannot be reordered
- First entry auto-promotes to `singing` if no current singer
- All DB mutations broadcast full queue to WebSocket clients
