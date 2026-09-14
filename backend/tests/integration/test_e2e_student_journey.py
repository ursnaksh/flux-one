import uuid
from datetime import datetime, time, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.enums import SubjectType
from app.models.institution import (
    College,
    Department,
    Division,
    Semester,
    Subject,
    TimetableSlot,
    Topic,
)
from app.repositories.session_repository import SessionRepository


@pytest.fixture
async def setup_vit_academic_catalog(db_session: AsyncSession):
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

    sub1 = Subject(
        semester_id=sem.id,
        name="Sensors and Transducers",
        code="IC2001",
        credits=4,
        subject_type=SubjectType.THEORY,
    )
    sub2 = Subject(
        semester_id=sem.id,
        name="Control Systems Principles",
        code="IC2002",
        credits=4,
        subject_type=SubjectType.THEORY,
    )
    db_session.add_all([sub1, sub2])
    await db_session.flush()

    topic = Topic(
        subject_id=sub1.id,
        unit_number=1,
        title="LVDT Sensors",
        description="Linear Variable Differential Transformer",
    )
    db_session.add(topic)

    # Add schedule slot for today
    today_weekday = datetime.now(timezone.utc).isoweekday()
    slot = TimetableSlot(
        semester_id=sem.id,
        division_id=div.id,
        subject_id=sub1.id,
        day_of_week=today_weekday,
        start_time=time(9, 0),
        end_time=time(10, 0),
        location="Room 1204",
        instructor_name="Prof. Kulkarni",
    )
    db_session.add(slot)
    await db_session.commit()

    return college, dept, sem, div, sub1, sub2, topic


@pytest.mark.asyncio
async def test_full_student_journey_and_metrics(db_session: AsyncSession, setup_vit_academic_catalog):
    college, dept, sem, div, sub1, sub2, topic = setup_vit_academic_catalog

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Student Registration (VIT Pune, Instrumentation, Sem 3, SEDA-D)
        reg_payload = {
            "email": "nagesh.shinde@vit.edu",
            "password": "StrongPassword123!",
            "full_name": "Nagesh Shinde",
            "prn_number": "12310456",
            "college_id": college.id,
            "department_id": dept.id,
            "division_id": div.id,
        }
        res_reg = await client.post("/api/v1/auth/register", json=reg_payload)
        assert res_reg.status_code == 201
        reg_data = res_reg.json()
        assert reg_data["email"] == "nagesh.shinde@vit.edu"
        assert len(reg_data["enrolled_subjects"]) == 2
        user_id = uuid.UUID(reg_data["id"])

        # Step 2: Login
        res_login = await client.post("/api/v1/auth/login", json={
            "email": "nagesh.shinde@vit.edu",
            "password": "StrongPassword123!",
        })
        assert res_login.status_code == 200
        tokens = res_login.json()
        token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 3: Initial Empty Dashboard Fetch
        res_dash_init = await client.get("/api/v1/dashboard/overview", headers=headers)
        assert res_dash_init.status_code == 200
        dash_init = res_dash_init.json()
        assert dash_init["student_name"] == "Nagesh Shinde"
        assert dash_init["college_name"] == "Vishwakarma Institute of Technology, Pune"
        assert dash_init["current_streak_days"] == 0
        assert dash_init["study_time_today_minutes"] == 0
        assert dash_init["active_session"] is None
        assert len(dash_init["enrolled_subjects"]) == 2
        assert len(dash_init["todays_schedule"]) == 1
        assert dash_init["todays_schedule"][0]["subject_code"] == "IC2001"

        # Step 4: Start Study Session on IC2001
        res_start = await client.post(
            "/api/v1/sessions/start",
            json={"subject_id": sub1.id, "topic_id": topic.id, "source": "MOBILE", "target_duration_minutes": 45},
            headers=headers,
        )
        assert res_start.status_code == 201
        session_id = res_start.json()["id"]

        # Step 5: Verify Active Session on Dashboard
        res_dash_active = await client.get("/api/v1/dashboard/overview", headers=headers)
        assert res_dash_active.status_code == 200
        dash_active = res_dash_active.json()
        assert dash_active["active_session"] is not None
        assert dash_active["active_session"]["id"] == session_id
        assert "Active session in progress" in dash_active["actionable_recommendation"]

        # Step 6: Simulate 30 Minutes of Study and Complete Session
        repo = SessionRepository(db_session)
        session_obj = await repo.get_by_id(uuid.UUID(session_id))
        session_obj.accumulated_active_seconds = 1800  # 30 minutes
        await repo.save_session(session_obj)
        await db_session.commit()

        res_complete = await client.post(
            f"/api/v1/sessions/{session_id}/complete",
            json={"focus_rating": 5, "reflection_note": "Understood the full differential LVDT derivation."},
            headers=headers,
        )
        assert res_complete.status_code == 200

        # Step 7: Verify Updated Dashboard (Streak=1, Minutes=30, Active=None)
        res_dash_done = await client.get("/api/v1/dashboard/overview", headers=headers)
        assert res_dash_done.status_code == 200
        dash_done = res_dash_done.json()
        assert dash_done["current_streak_days"] == 1
        assert dash_done["study_time_today_minutes"] == 30
        assert dash_done["active_session"] is None
        assert dash_done["consistency_score"] == 100.0

        # Step 8: Query System Operational Metrics (Requires X-Admin-Secret)
        # Without secret -> 422 / 403
        res_unauth_metrics = await client.get("/internal/metrics")
        assert res_unauth_metrics.status_code in [403, 422]

        # With secret -> 200 OK
        admin_headers = {"X-Admin-Secret": settings.ADMIN_METRICS_SECRET}
        res_metrics = await client.get("/internal/metrics", headers=admin_headers)
        assert res_metrics.status_code == 200
        metrics = res_metrics.json()
        assert metrics["total_registered_users"] == 1
        assert metrics["active_sessions_now"] == 0
        assert metrics["sessions_completed_today"] == 1
        assert metrics["study_minutes_today"] == 30
        assert metrics["global_average_focus"] == 5.0

    app.dependency_overrides.clear()
