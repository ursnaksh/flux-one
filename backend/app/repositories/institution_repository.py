from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.institution import (
    College,
    Department,
    Division,
    Semester,
    Subject,
    Topic,
    TimetableSlot,
)


class InstitutionRepository:
    """
    Persistence boundary for the Institutional Catalog.
    Exposes only business-safe accessors and encapsulates all SQLAlchemy query logic.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_college_by_code(self, code: str) -> Optional[College]:
        stmt = select(College).where(College.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_colleges_with_hierarchy(self) -> List[College]:
        """
        Retrieves the complete institutional hierarchy for student onboarding drop-downs.
        Uses selectinload to prevent N+1 query degradation.
        """
        stmt = (
            select(College)
            .options(
                selectinload(College.departments)
                .selectinload(Department.semesters)
                .selectinload(Semester.divisions)
            )
            .order_by(College.name.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_division_by_id(self, division_id: int) -> Optional[Division]:
        stmt = select(Division).where(Division.id == division_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_division_subjects(self, division_id: int) -> List[Subject]:
        """
        Fetches all subjects linked to the semester belonging to the specified division.
        """
        stmt = (
            select(Subject)
            .join(Semester, Subject.semester_id == Semester.id)
            .join(Division, Division.semester_id == Semester.id)
            .options(selectinload(Subject.topics))
            .where(Division.id == division_id)
            .order_by(Subject.code.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_division_timetable(self, division_id: int) -> List[TimetableSlot]:
        """
        Retrieves weekly scheduled timetable slots for a division ordered by day and start time.
        """
        stmt = (
            select(TimetableSlot)
            .options(selectinload(TimetableSlot.subject))
            .where(TimetableSlot.division_id == division_id)
            .order_by(TimetableSlot.day_of_week.asc(), TimetableSlot.start_time.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
