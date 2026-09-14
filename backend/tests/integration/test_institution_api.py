from datetime import time
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.enums import SubjectType
from app.models.institution import (
    College,
    Department,
    Division,
    Semester,
    Subject,
    Topic,
    TimetableSlot,
)


@pytest.mark.asyncio
async def test_institution_hierarchy_and_curriculum(db_session: AsyncSession):
    # 1. Seed Fixture Data into the test session
    college = College(
        name="Vishwakarma Institute of Technology, Pune",
        code="VIT_PUNE",
        city="Pune",
        time_zone="Asia/Kolkata",
    )
    db_session.add(college)
    await db_session.flush()

    dept = Department(
        college_id=college.id,
        name="Instrumentation and Control Engineering",
        code="INFT_INST",
    )
    db_session.add(dept)
    await db_session.flush()

    sem = Semester(
        department_id=dept.id,
        semester_number=3,
        academic_year="2026-2027",
    )
    db_session.add(sem)
    await db_session.flush()

    div = Division(
        semester_id=sem.id,
        name="SEDA - Division D",
    )
    db_session.add(div)
    await db_session.flush()

    sub = Subject(
        semester_id=sem.id,
        name="Sensors and Transducers",
        code="IC2001",
        credits=4,
        subject_type=SubjectType.THEORY,
    )
    db_session.add(sub)
    await db_session.flush()

    topic = Topic(
        subject_id=sub.id,
        unit_number=1,
        title="Displacement Sensors: LVDT",
        description="Differential transformer theory",
    )
    db_session.add(topic)

    slot = TimetableSlot(
        semester_id=sem.id,
        division_id=div.id,
        subject_id=sub.id,
        day_of_week=1,
        start_time=time(9, 0),
        end_time=time(10, 0),
        location="Room 1204",
        instructor_name="Prof. Kulkarni",
    )
    db_session.add(slot)
    await db_session.commit()

    # 2. Dependency Override
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test Hierarchy
        res_hier = await client.get("/api/v1/institution/hierarchy")
        assert res_hier.status_code == 200
        hier_data = res_hier.json()
        assert len(hier_data) == 1
        assert hier_data[0]["code"] == "VIT_PUNE"
        assert hier_data[0]["departments"][0]["code"] == "INFT_INST"
        assert hier_data[0]["departments"][0]["semesters"][0]["semester_number"] == 3
        assert hier_data[0]["departments"][0]["semesters"][0]["divisions"][0]["name"] == "SEDA - Division D"

        # Test Division Curriculum
        res_curr = await client.get(f"/api/v1/institution/divisions/{div.id}/curriculum")
        assert res_curr.status_code == 200
        curr_data = res_curr.json()
        assert len(curr_data) == 1
        assert curr_data[0]["code"] == "IC2001"
        assert curr_data[0]["subject_type"] == "THEORY"
        assert len(curr_data[0]["topics"]) == 1
        assert curr_data[0]["topics"][0]["title"] == "Displacement Sensors: LVDT"

        # Test Division Timetable
        res_tt = await client.get(f"/api/v1/institution/divisions/{div.id}/timetable")
        assert res_tt.status_code == 200
        tt_data = res_tt.json()
        assert len(tt_data) == 1
        assert tt_data[0]["day_of_week"] == 1
        assert tt_data[0]["location"] == "Room 1204"
        assert tt_data[0]["subject_code"] == "IC2001"
        assert tt_data[0]["instructor_name"] == "Prof. Kulkarni"

        # Test Invalid Division (404)
        res_invalid = await client.get("/api/v1/institution/divisions/99999/curriculum")
        assert res_invalid.status_code == 404
        err_data = res_invalid.json()
        assert err_data["success"] is False
        assert err_data["error_code"] == "HTTP_EXCEPTION"

    app.dependency_overrides.clear()
