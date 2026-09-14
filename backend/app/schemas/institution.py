from datetime import time
from typing import List, Optional
from pydantic import BaseModel
from app.models.enums import SubjectType


class TopicResponse(BaseModel):
    id: int
    unit_number: int
    title: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class SubjectCurriculumResponse(BaseModel):
    id: int
    name: str
    code: str
    credits: int
    subject_type: SubjectType
    topics: List[TopicResponse] = []

    class Config:
        from_attributes = True


class DivisionHierarchyResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class SemesterHierarchyResponse(BaseModel):
    id: int
    semester_number: int
    academic_year: str
    divisions: List[DivisionHierarchyResponse] = []

    class Config:
        from_attributes = True


class DepartmentHierarchyResponse(BaseModel):
    id: int
    name: str
    code: str
    semesters: List[SemesterHierarchyResponse] = []

    class Config:
        from_attributes = True


class CollegeHierarchyResponse(BaseModel):
    id: int
    name: str
    code: str
    city: str
    time_zone: str
    departments: List[DepartmentHierarchyResponse] = []

    class Config:
        from_attributes = True


class TimetableSlotResponse(BaseModel):
    id: int
    day_of_week: int
    start_time: time
    end_time: time
    location: str
    instructor_name: Optional[str] = None
    subject_name: str
    subject_code: str

    class Config:
        from_attributes = True
