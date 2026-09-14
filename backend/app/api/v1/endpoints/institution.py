from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.institution_repository import InstitutionRepository
from app.schemas.institution import (
    CollegeHierarchyResponse,
    SubjectCurriculumResponse,
    TimetableSlotResponse,
)

router = APIRouter()


@router.get("/hierarchy", response_model=List[CollegeHierarchyResponse])
async def get_institution_hierarchy(db: AsyncSession = Depends(get_db)):
    """
    Returns the complete institutional hierarchy (Colleges -> Departments -> Semesters -> Divisions)
    to drive zero-friction mobile student onboarding.
    """
    repo = InstitutionRepository(db)
    return await repo.list_colleges_with_hierarchy()


@router.get("/divisions/{division_id}/curriculum", response_model=List[SubjectCurriculumResponse])
async def get_division_curriculum(division_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns all subjects and syllabus topics associated with the semester of the given division.
    """
    repo = InstitutionRepository(db)
    division = await repo.get_division_by_id(division_id)
    if not division:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Division with ID {division_id} not found.",
        )

    subjects = await repo.get_division_subjects(division_id)
    return subjects


@router.get("/divisions/{division_id}/timetable", response_model=List[TimetableSlotResponse])
async def get_division_timetable(division_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns the weekly class schedule for the given division.
    """
    repo = InstitutionRepository(db)
    division = await repo.get_division_by_id(division_id)
    if not division:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Division with ID {division_id} not found.",
        )

    slots = await repo.get_division_timetable(division_id)
    return [
        TimetableSlotResponse(
            id=slot.id,
            day_of_week=slot.day_of_week,
            start_time=slot.start_time,
            end_time=slot.end_time,
            location=slot.location,
            instructor_name=slot.instructor_name,
            subject_name=slot.subject.name,
            subject_code=slot.subject.code,
        )
        for slot in slots
    ]
