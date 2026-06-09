from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from backend.models import QueueEntry, QueueStatusEnum
from backend.schemas import QueueEntry as QueueEntrySchema


class QueueService:
    @staticmethod
    async def get_full_queue(db: AsyncSession) -> list[QueueEntrySchema]:
        """Get queue: singing first, then waiting by position, then done"""
        query = select(QueueEntry).order_by(
            # Custom sort: singing first, then waiting by position, then done by created_at
            case(
                (QueueEntry.status == QueueStatusEnum.singing, 0),
                (QueueEntry.status == QueueStatusEnum.waiting, 1),
                (QueueEntry.status == QueueStatusEnum.done, 2),
            ),
            QueueEntry.position,
            QueueEntry.created_at,
        )
        result = await db.execute(query)
        entries = result.scalars().all()
        return [QueueEntrySchema.model_validate(e) for e in entries]

    @staticmethod
    async def add_entry(db: AsyncSession, singer: str, song: str) -> QueueEntrySchema:
        """Add new entry to queue"""
        # Get max position for waiting entries
        max_pos_query = select(func.coalesce(func.max(QueueEntry.position), 0)).where(
            QueueEntry.status == QueueStatusEnum.waiting
        )
        result = await db.execute(max_pos_query)
        max_position = result.scalar()

        # Check if there's a current singer
        singing_query = select(QueueEntry).where(
            QueueEntry.status == QueueStatusEnum.singing
        )
        result = await db.execute(singing_query)
        current_singer = result.scalar()

        # Auto-promote if no current singer
        status = QueueStatusEnum.singing if not current_singer else QueueStatusEnum.waiting
        position = 0 if status == QueueStatusEnum.singing else max_position + 1

        new_entry = QueueEntry(
            singer=singer, song=song, status=status, position=position
        )
        db.add(new_entry)
        await db.commit()
        await db.refresh(new_entry)
        return QueueEntrySchema.model_validate(new_entry)

    @staticmethod
    async def move_waiting_entry(
        db: AsyncSession, entry_id: int, new_position: int
    ) -> QueueEntrySchema:
        """Move a waiting entry to a new position"""
        query = select(QueueEntry).where(QueueEntry.id == entry_id)
        result = await db.execute(query)
        entry = result.scalar_one_or_none()

        if not entry or entry.status != QueueStatusEnum.waiting:
            return None

        # Get all waiting entries
        waiting_query = select(QueueEntry).where(
            QueueEntry.status == QueueStatusEnum.waiting
        ).order_by(QueueEntry.position)
        result = await db.execute(waiting_query)
        waiting_entries = result.scalars().all()

        # Remove from current position
        waiting_entries = [e for e in waiting_entries if e.id != entry_id]

        # Insert at new position
        waiting_entries.insert(min(new_position, len(waiting_entries)), entry)

        # Update all positions
        for idx, e in enumerate(waiting_entries):
            e.position = idx

        await db.commit()

        # Refresh and return
        await db.refresh(entry)
        return QueueEntrySchema.model_validate(entry)

    @staticmethod
    async def next_singer(db: AsyncSession) -> bool:
        """Mark current singing as done, promote next waiting"""
        # Find current singer
        singing_query = select(QueueEntry).where(
            QueueEntry.status == QueueStatusEnum.singing
        )
        result = await db.execute(singing_query)
        current = result.scalar_one_or_none()

        if not current:
            return False

        # Mark as done
        current.status = QueueStatusEnum.done

        # Find next waiting (lowest position)
        next_query = select(QueueEntry).where(
            QueueEntry.status == QueueStatusEnum.waiting
        ).order_by(QueueEntry.position).limit(1)
        result = await db.execute(next_query)
        next_entry = result.scalar_one_or_none()

        if next_entry:
            next_entry.status = QueueStatusEnum.singing
            next_entry.position = 0

        await db.commit()
        return True
