import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import College, Department, Semester, Division, Subject, Topic


@pytest.mark.asyncio
async def test_study_session_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # Setup baseline data
    college = College(name="VIT Pune", code="VIT_PUNE", city="Pune")
    db_session.add(college)
    await db_session.flush()

    dept = Department(college_id=college.id, name="Instrumentation", code="INST")
    db_session.add(dept)
    await db_session.flush()

    sem = Semester(department_id=dept.id, semester_number=3, academic_year="2026-2027")
    db_session.add(sem)
    await db_session.flush()

    div = Division(semester_id=sem.id, name="SEDA - Division D")
    db_session.add(div)
    await db_session.flush()

    sub = Subject(semester_id=sem.id, name="Sensors", code="IC2001", credits=4, subject_type="THEORY")
    db_session.add(sub)
    await db_session.flush()

    topic = Topic(subject_id=sub.id, unit_number=1, title="LVDT Transducers")
    db_session.add(topic)
    await db_session.commit()

    # Register & Login
    await client.post("/api/v1/auth/register", json={
        "email": "study_user@vit.edu",
        "password": "Password123!",
        "full_name": "Study Student",
        "college_id": college.id,
        "department_id": dept.id,
        "division_id": div.id,
    })
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "study_user@vit.edu",
        "password": "Password123!",
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Start Session
    start_res = await client.post(
        "/api/v1/sessions/start",
        json={"subject_id": sub.id, "topic_id": topic.id, "source": "MANUAL", "target_duration_minutes": 45},
        headers=headers,
    )
    assert start_res.status_code == 201
    session_data = start_res.json()
    session_id = session_data["id"]

    # 2. Prevent concurrent active session
    dup_res = await client.post(
        "/api/v1/sessions/start",
        json={"subject_id": sub.id, "topic_id": topic.id},
        headers=headers,
    )
    assert dup_res.status_code == 400

    # 3. Check Active Session endpoint
    active_res = await client.get("/api/v1/sessions/active", headers=headers)
    assert active_res.status_code == 200
    assert active_res.json()["id"] == session_id

    # 4. Heartbeat
    hb_res = await client.post(
        f"/api/v1/sessions/{session_id}/heartbeat",
        json={"current_active_minutes": 30},
        headers=headers,
    )
    assert hb_res.status_code == 200
    assert hb_res.json()["duration_minutes"] >= 30

    # 5. End Session with Reflection
    end_res = await client.post(
        f"/api/v1/sessions/{session_id}/end",
        json={"focus_rating": 5, "reflection_note": "Understood the full equation."},
        headers=headers,
    )
    assert end_res.status_code == 200
    ended_data = end_res.json()
    assert ended_data["end_time"] is not None
    assert ended_data["focus_rating"] == 5

    # 6. Active session is now cleared
    active_after = await client.get("/api/v1/sessions/active", headers=headers)
    assert active_after.status_code == 200
    assert active_after.json() is None
