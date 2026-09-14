import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.enums import SessionSource, SessionStatus, SubjectType
from app.models.institution import College, Department, Division, Semester, Subject, Topic
from app.models.session import StudySession
from app.repositories.session_repository import SessionRepository


@pytest.fixture
async def setup_student_and_course(db_session: AsyncSession):
    # 1. Catalog
    college = College(name="VIT Pune", code="VIT_PUNE", city="Pune")
    db_session.add(college)
    await db_session.flush()

    dept = Department(college_id=college.id, name="Instrumentation", code="INFT_INST")
    db_session.add(dept)
    await db_session.flush()

    sem = Semester(department_id=dept.id, semester_number=3, academic_year="2026-2027")
    db_session.add(sem)
    await db_session.flush()

    div = Division(semester_id=sem.id, name="SEDA - Division D")
    db_session.add(div)
    await db_session.flush()

    sub = Subject(semester_id=sem.id, name="Sensors", code="IC2001", credits=4, subject_type=SubjectType.THEORY)
    db_session.add(sub)
    await db_session.flush()

    topic = Topic(subject_id=sub.id, unit_number=1, title="LVDT Sensors", description="Differential transformer")
    db_session.add(topic)
    await db_session.commit()

    return college, dept, sem, div, sub, topic


@pytest.mark.asyncio
async def test_session_state_machine_and_streak_lifecycle(db_session: AsyncSession, setup_student_and_course):
    college, dept, sem, div, sub, topic = setup_student_and_course

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register student
        reg_res = await client.post("/api/v1/auth/register", json={
            "email": "session.tester@vit.edu",
            "password": "StrongPassword123!",
            "full_name": "Session Tester",
            "college_id": college.id,
            "department_id": dept.id,
            "division_id": div.id,
        })
        assert reg_res.status_code == 201

        # 2. Login
        login_res = await client.post("/api/v1/auth/login", json={
            "email": "session.tester@vit.edu",
            "password": "StrongPassword123!",
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create Session (ACTIVE)
        start_payload = {
            "subject_id": sub.id,
            "topic_id": topic.id,
            "target_duration_minutes": 45,
            "source": "MOBILE",
        }
        start_res = await client.post("/api/v1/sessions/start", json=start_payload, headers=headers)
        assert start_res.status_code == 201
        session_data = start_res.json()
        assert session_data["status"] == "ACTIVE"
        session_id = session_data["id"]

        # 4. Rejection of Duplicate Active Session
        dup_res = await client.post("/api/v1/sessions/start", json=start_payload, headers=headers)
        assert dup_res.status_code == 400
        assert "already in progress" in dup_res.json()["message"].lower()

        # 5. Heartbeat Update
        hb_res = await client.post(f"/api/v1/sessions/{session_id}/heartbeat", json={}, headers=headers)
        assert hb_res.status_code == 200

        # 6. Pause Session (ACTIVE -> PAUSED)
        pause_res = await client.post(f"/api/v1/sessions/{session_id}/pause", headers=headers)
        assert pause_res.status_code == 200
        assert pause_res.json()["status"] == "PAUSED"

        # 7. Resume Session (PAUSED -> ACTIVE)
        resume_res = await client.post(f"/api/v1/sessions/{session_id}/resume", headers=headers)
        assert resume_res.status_code == 200
        assert resume_res.json()["status"] == "ACTIVE"

        # 8. Complete Session (ACTIVE -> COMPLETED)
        # Manually inflate accumulated seconds in DB to simulate 25 minutes of active study (>=20 min qualifying)
        repo = SessionRepository(db_session)
        db_session_obj = await repo.get_by_id(uuid.UUID(session_id))
        db_session_obj.accumulated_active_seconds = 1500  # 25 minutes
        await repo.save_session(db_session_obj)
        await db_session.commit()

        complete_payload = {
            "focus_rating": 5,
            "reflection_note": "Great session on LVDT differential equations.",
        }
        complete_res = await client.post(
            f"/api/v1/sessions/{session_id}/complete",
            json=complete_payload,
            headers=headers,
        )
        assert complete_res.status_code == 200
        completed_data = complete_res.json()
        assert completed_data["status"] == "COMPLETED"
        assert completed_data["duration_minutes"] == 25
        assert completed_data["focus_rating"] == 5

        # 9. Verify Atomic Streak & Stats Update
        streak = await repo.get_user_streak(uuid.UUID(session_data["user_id"]))
        brain = await repo.get_user_academic_brain(uuid.UUID(session_data["user_id"]))
        assert streak.current_streak == 1
        assert streak.longest_streak == 1
        assert brain.total_study_minutes == 25
        assert brain.average_focus_rating == 5.0

        # 10. Second Qualifying Session on Same Day: Streak does NOT increment again!
        second_start = await client.post("/api/v1/sessions/start", json=start_payload, headers=headers)
        assert second_start.status_code == 201
        session_id_2 = second_start.json()["id"]

        session_2_obj = await repo.get_by_id(uuid.UUID(session_id_2))
        session_2_obj.accumulated_active_seconds = 1800  # 30 minutes
        await repo.save_session(session_2_obj)
        await db_session.commit()

        await client.post(
            f"/api/v1/sessions/{session_id_2}/complete",
            json={"focus_rating": 4, "reflection_note": "Second session today"},
            headers=headers,
        )

        streak_after = await repo.get_user_streak(uuid.UUID(session_data["user_id"]))
        brain_after = await repo.get_user_academic_brain(uuid.UUID(session_data["user_id"]))
        assert streak_after.current_streak == 1  # Streak remained 1!
        assert brain_after.total_study_minutes == 55  # 25 + 30 = 55 minutes

        # 11. Stale Session Auto-Reconciliation
        # Start a 3rd session, set heartbeat to 3 hours ago, then call start again -> auto-abandoned!
        third_start = await client.post("/api/v1/sessions/start", json=start_payload, headers=headers)
        assert third_start.status_code == 201
        session_id_3 = third_start.json()["id"]

        session_3_obj = await repo.get_by_id(uuid.UUID(session_id_3))
        session_3_obj.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(hours=3)
        await repo.save_session(session_3_obj)
        await db_session.commit()

        # Starting a new session now auto-reconciles and auto-abandons session 3!
        fourth_start = await client.post("/api/v1/sessions/start", json=start_payload, headers=headers)
        assert fourth_start.status_code == 201

        # Check session 3 status
        session_3_refreshed = await repo.get_by_id(uuid.UUID(session_id_3))
        assert session_3_refreshed.status == SessionStatus.ABANDONED

        # 12. Future AI Hook (Session Summary Endpoint)
        summary_res = await client.get(f"/api/v1/sessions/{session_id}/summary", headers=headers)
        assert summary_res.status_code == 200
        summary_data = summary_res.json()
        assert summary_data["subject_name"] == "Sensors"
        assert summary_data["duration_minutes"] == 25
        assert summary_data["student_current_streak"] == 1

    app.dependency_overrides.clear()
