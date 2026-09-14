import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import College, Department, Semester, Division, Subject


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient, db_session: AsyncSession):
    # Setup test college, department, semester, division, and subjects
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

    sub1 = Subject(semester_id=sem.id, name="Sensors", code="IC2001", credits=4, subject_type="THEORY")
    sub2 = Subject(semester_id=sem.id, name="Control Systems", code="IC2002", credits=4, subject_type="THEORY")
    db_session.add_all([sub1, sub2])
    await db_session.commit()

    # 1. Register student
    register_payload = {
        "email": "student@vit.edu",
        "password": "Password123!",
        "full_name": "Nagesh Shinde",
        "prn_number": "12310001",
        "college_id": college.id,
        "department_id": dept.id,
        "division_id": div.id,
    }
    response = await client.post("/api/v1/auth/register", json=register_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "student@vit.edu"
    assert len(data["enrolled_subjects"]) == 2

    # 2. Login
    login_payload = {
        "email": "student@vit.edu",
        "password": "Password123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 3. Access Protected /me route
    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["full_name"] == "Nagesh Shinde"
    assert len(me_data["enrolled_subjects"]) == 2
