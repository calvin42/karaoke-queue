# Karaoke Queue

A full-stack real-time karaoke queue web app for smartphone use.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLite (SQLAlchemy + aiosqlite), WebSockets
- **Frontend**: Single HTML file + CSS + vanilla JS
- **Tests**: pytest + pytest-asyncio + httpx

## Features

- Real-time queue updates via WebSocket
- Position number input for reordering queue entries
- Dark/light mode toggle
- Mobile-first responsive design (375px)
- Auto-reconnect WebSocket on disconnect


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

