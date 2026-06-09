import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.models import Base
from backend.database import get_db
from backend.main import app


@pytest.fixture
async def test_db():
    """Create test database"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncTestSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with AsyncTestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield AsyncTestSessionLocal

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(test_db):
    """Create test client"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_empty_queue(client):
    """Test GET /queue with empty queue"""
    response = await client.get("/queue")
    assert response.status_code == 200
    data = response.json()
    assert data["queue"] == []


@pytest.mark.asyncio
async def test_post_queue_waiting(client):
    """Test POST /queue creates entry with status waiting"""
    response = await client.post(
        "/queue",
        json={"singer": "Alice", "song": "Bohemian Rhapsody"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["singer"] == "Alice"
    assert data["song"] == "Bohemian Rhapsody"
    assert data["status"] == "singing"  # First entry auto-promotes to singing
    assert data["position"] == 0


@pytest.mark.asyncio
async def test_first_entry_auto_singing(client):
    """Test first entry auto-promotes to singing"""
    response = await client.post(
        "/queue",
        json={"singer": "Alice", "song": "Song 1"}
    )
    assert response.status_code == 201
    assert response.json()["status"] == "singing"


@pytest.mark.asyncio
async def test_second_entry_waiting(client):
    """Test second entry is waiting"""
    await client.post("/queue", json={"singer": "Alice", "song": "Song 1"})
    response = await client.post("/queue", json={"singer": "Bob", "song": "Song 2"})
    assert response.status_code == 201
    assert response.json()["status"] == "waiting"


@pytest.mark.asyncio
async def test_next_singer(client):
    """Test POST /queue/next marks singing as done and promotes next"""
    # Add two entries
    alice = await client.post("/queue", json={"singer": "Alice", "song": "Song 1"})
    bob = await client.post("/queue", json={"singer": "Bob", "song": "Song 2"})

    # Move to next
    response = await client.post("/queue/next")
    assert response.status_code == 200

    # Check queue state
    queue_response = await client.get("/queue")
    queue = queue_response.json()["queue"]

    # Alice should be done
    alice_entry = next(e for e in queue if e["id"] == alice.json()["id"])
    assert alice_entry["status"] == "done"

    # Bob should be singing
    bob_entry = next(e for e in queue if e["id"] == bob.json()["id"])
    assert bob_entry["status"] == "singing"


@pytest.mark.asyncio
async def test_patch_done_entry_fails(client):
    """Test PATCH on done entry returns 400"""
    # Add and complete an entry
    response = await client.post("/queue", json={"singer": "Alice", "song": "Song 1"})
    entry_id = response.json()["id"]

    await client.post("/queue/next")

    # Try to move done entry
    move_response = await client.patch(
        f"/queue/{entry_id}/move?new_position=0"
    )
    assert move_response.status_code == 400


@pytest.mark.asyncio
async def test_patch_singing_entry_fails(client):
    """Test PATCH on singing entry returns 400"""
    # Add entry (auto-singing)
    response = await client.post("/queue", json={"singer": "Alice", "song": "Song 1"})
    entry_id = response.json()["id"]

    # Try to move singing entry
    move_response = await client.patch(
        f"/queue/{entry_id}/move?new_position=1"
    )
    assert move_response.status_code == 400


@pytest.mark.asyncio
async def test_queue_order(client):
    """Test queue returns: singing, waiting by position, done"""
    # Add entries
    alice = await client.post("/queue", json={"singer": "Alice", "song": "Song 1"})
    bob = await client.post("/queue", json={"singer": "Bob", "song": "Song 2"})
    charlie = await client.post("/queue", json={"singer": "Charlie", "song": "Song 3"})

    # Move to next
    await client.post("/queue/next")

    # Get queue
    queue_response = await client.get("/queue")
    queue = queue_response.json()["queue"]

    assert len(queue) == 3
    assert queue[0]["status"] == "singing"
    assert queue[0]["singer"] == "Bob"
    assert queue[1]["status"] == "waiting"
    assert queue[1]["singer"] == "Charlie"
    assert queue[2]["status"] == "done"
    assert queue[2]["singer"] == "Alice"
