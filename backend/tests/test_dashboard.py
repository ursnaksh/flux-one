import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import College, Department, Semester, Division, Subject, Topic


@pytest.mark.asyncio
async def test_dashboard_overview_aggregation(client: AsyncClient, db_session: AsyncSession):
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

    topic = Topic(subject_id=sub.id, unit_number=1, title="LVDT")
    db_session.add(topic)
    await db_session.commit()

    # Register & Login
    await client.post("/api/v1/auth/register", json={
        "email": "dash_student@vit.edu",
        "password": "Password123!",
        "full_name": "Dash User",
        "college_id": college.id,
        "department_id": dept.id,
        "division_id": div.id,
    })
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "dash_student@vit.edu",
        "password": "Password123!",
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Complete a session to populate metrics
    start_res = await client.post(
        "/api/v1/sessions/start",
        json={"subject_id": sub.id, "topic_id": topic.id, "target_duration_minutes": 40},
        headers=headers,
    )
    session_id = start_res.json()["id"]

    await client.post(
        f"/api/v1/sessions/{session_id}/heartbeat",
        json={"current_active_minutes": 40},
        headers=headers,
    )

    await client.post(
        f"/api/v1/sessions/{session_id}/end",
        json={"focus_rating": 4, "reflection_note": "Good focus."},
        headers=headers,
    )

    # Fetch Dashboard Overview in 1 call
    dash_res = await client.get("/api/v1/dashboard/overview", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()

    assert dash_data["student_name"] == "Dash User"
    assert dash_data["college_name"] == "VIT Pune"
    assert dash_data["current_streak_days"] == 1
    assert dash_data["study_time_today_minutes"] >= 40
    assert dash_data["active_session"] is None
    assert len(dash_data["top_weak_topics"]) == 1
    assert dash_data["top_weak_topics"][0]["topic_id"] == topic.id
    assert "streak" in dash_data["ai_recommendation"].lower() or "session" in dash_data["ai_recommendation"].lower()
