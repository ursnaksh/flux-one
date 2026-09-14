import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.enums import SubjectType
from app.models.institution import College, Department, Division, Semester, Subject
from app.repositories.user_repository import UserRepository


@pytest.fixture
async def seeded_catalog(db_session: AsyncSession):
    # Primary College: VIT Pune
    college = College(name="Vishwakarma Institute of Technology, Pune", code="VIT_PUNE", city="Pune", time_zone="Asia/Kolkata")
    db_session.add(college)
    await db_session.flush()

    dept = Department(college_id=college.id, name="Instrumentation and Control Engineering", code="INFT_INST")
    db_session.add(dept)
    await db_session.flush()

    sem = Semester(department_id=dept.id, semester_number=3, academic_year="2026-2027")
    db_session.add(sem)
    await db_session.flush()

    div = Division(semester_id=sem.id, name="SEDA - Division D")
    db_session.add(div)
    await db_session.flush()

    # Exact 7 Core Subjects for Semester 3
    subjects_data = [
        ("Sensors and Transducers", "IC2303", 4, SubjectType.THEORY),
        ("Data Science", "IC2301", 4, SubjectType.THEORY),
        ("Microcontroller & Applications", "MM1408", 4, SubjectType.THEORY),
        ("Object Oriented Programming", "IC2305", 4, SubjectType.THEORY),
        ("Database Management Systems", "IC2307", 4, SubjectType.THEORY),
        ("Reasoning & Aptitude Development - 3", "HS2001", 2, SubjectType.THEORY),
        ("Design Thinking - 1", "IC2311", 1, SubjectType.PROJECT),
    ]
    created_subjects = []
    for name, code, credits, stype in subjects_data:
        subj = Subject(semester_id=sem.id, name=name, code=code, credits=credits, subject_type=stype)
        db_session.add(subj)
        created_subjects.append(subj)
    await db_session.flush()

    # Secondary College & Dept for cross-institution mismatch testing
    other_college = College(name="COEP Technological University", code="COEP", city="Pune", time_zone="Asia/Kolkata")
    db_session.add(other_college)
    await db_session.flush()

    other_dept = Department(college_id=other_college.id, name="Mechanical Engineering", code="MECH")
    db_session.add(other_dept)
    await db_session.flush()

    other_sem = Semester(department_id=other_dept.id, semester_number=3, academic_year="2026-2027")
    db_session.add(other_sem)
    await db_session.flush()

    other_div = Division(semester_id=other_sem.id, name="MECH - Div A")
    db_session.add(other_div)
    await db_session.commit()

    return college, dept, sem, div, created_subjects, other_college, other_dept, other_sem, other_div


@pytest.mark.asyncio
async def test_auth_full_lifecycle_and_hierarchy_validation(db_session: AsyncSession, seeded_catalog):
    college, dept, sem, div, subjects, other_college, other_dept, other_sem, other_div = seeded_catalog

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Weak Password Rejection (HTTP 422)
        weak_pwd_payload = {
            "email": "student@vit.edu",
            "password": "weakpassword123",
            "full_name": "Student User",
            "college_id": college.id,
            "department_id": dept.id,
            "division_id": div.id,
        }
        res_weak = await client.post("/api/v1/auth/register", json=weak_pwd_payload)
        assert res_weak.status_code == 422
        assert "complexity" in res_weak.json()["message"].lower()

        # 2. Invalid College Rejection (HTTP 400)
        invalid_college_payload = dict(weak_pwd_payload)
        invalid_college_payload["password"] = "StrongPassword123!"
        invalid_college_payload["college_id"] = 99999
        res_inv_col = await client.post("/api/v1/auth/register", json=invalid_college_payload)
        assert res_inv_col.status_code == 400
        assert "college with id 99999 does not exist" in res_inv_col.json()["message"].lower()

        # 3. Department Belonging to Another College Rejection (HTTP 400)
        dept_mismatch_payload = dict(weak_pwd_payload)
        dept_mismatch_payload["password"] = "StrongPassword123!"
        dept_mismatch_payload["department_id"] = other_dept.id
        res_dept_mismatch = await client.post("/api/v1/auth/register", json=dept_mismatch_payload)
        assert res_dept_mismatch.status_code == 400
        assert "does not belong to college" in res_dept_mismatch.json()["message"].lower()

        # 4. Invalid Division Rejection (HTTP 400)
        invalid_div_payload = dict(weak_pwd_payload)
        invalid_div_payload["password"] = "StrongPassword123!"
        invalid_div_payload["division_id"] = 99999
        res_inv_div = await client.post("/api/v1/auth/register", json=invalid_div_payload)
        assert res_inv_div.status_code == 400
        assert "division with id 99999 does not exist" in res_inv_div.json()["message"].lower()

        # 5. Division Inconsistent with Department/College (HTTP 400)
        div_mismatch_payload = dict(weak_pwd_payload)
        div_mismatch_payload["password"] = "StrongPassword123!"
        div_mismatch_payload["division_id"] = other_div.id
        res_div_mismatch = await client.post("/api/v1/auth/register", json=div_mismatch_payload)
        assert res_div_mismatch.status_code == 400
        assert "does not belong to the chosen department" in res_div_mismatch.json()["message"].lower()

        # 6. Provided Semester Inconsistent with Division (HTTP 400)
        sem_mismatch_payload = dict(weak_pwd_payload)
        sem_mismatch_payload["password"] = "StrongPassword123!"
        sem_mismatch_payload["semester_id"] = other_sem.id
        res_sem_mismatch = await client.post("/api/v1/auth/register", json=sem_mismatch_payload)
        assert res_sem_mismatch.status_code == 400
        assert "does not match the division's semester" in res_sem_mismatch.json()["message"].lower()

        # 7. Successful Registration & Automatic Enrollment of all 7 VIT Subjects (HTTP 201)
        valid_reg_payload = {
            "email": "student@vit.edu",
            "password": "StrongPassword123!",
            "full_name": "Student User",
            "prn_number": "12310456",
            "college_id": college.id,
            "department_id": dept.id,
            "division_id": div.id,
            "semester_id": sem.id,
        }
        res_reg = await client.post("/api/v1/auth/register", json=valid_reg_payload)
        assert res_reg.status_code == 201
        reg_data = res_reg.json()
        assert reg_data["email"] == "student@vit.edu"
        assert reg_data["full_name"] == "Student User"
        assert reg_data["prn_number"] == "12310456"
        assert reg_data["college_id"] == college.id
        assert reg_data["department_id"] == dept.id
        assert reg_data["division_id"] == div.id
        assert reg_data["semester_id"] == sem.id
        assert len(reg_data["enrolled_subjects"]) == 7

        enrolled_codes = [s["code"] for s in reg_data["enrolled_subjects"]]
        assert "IC2303" in enrolled_codes
        assert "IC2301" in enrolled_codes
        assert "MM1408" in enrolled_codes
        assert "IC2305" in enrolled_codes
        assert "IC2307" in enrolled_codes
        assert "HS2001" in enrolled_codes
        assert "IC2311" in enrolled_codes

        # 8. Duplicate Email Rejection (HTTP 400)
        res_dup_email = await client.post("/api/v1/auth/register", json=valid_reg_payload)
        assert res_dup_email.status_code == 400
        assert "email already registered" in res_dup_email.json()["message"].lower()

        # 9. Duplicate PRN Rejection (HTTP 400)
        dup_prn_payload = dict(valid_reg_payload)
        dup_prn_payload["email"] = "other.student@vit.edu"
        res_dup_prn = await client.post("/api/v1/auth/register", json=dup_prn_payload)
        assert res_dup_prn.status_code == 400
        assert "prn number already registered" in res_dup_prn.json()["message"].lower()

        # 10. Login Failure (Wrong Password)
        res_login_fail = await client.post(
            "/api/v1/auth/login",
            json={"email": "student@vit.edu", "password": "WrongPassword123!"},
        )
        assert res_login_fail.status_code == 401
        assert res_login_fail.json()["message"] == "Invalid email or password."

        # 11. Login Success After Registration (HTTP 200)
        res_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "student@vit.edu", "password": "StrongPassword123!"},
        )
        assert res_login.status_code == 200
        tokens = res_login.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # 12. Access Protected /auth/me with Returned Access Token (HTTP 200)
        res_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert res_me.status_code == 200
        me_data = res_me.json()
        assert me_data["email"] == "student@vit.edu"
        assert me_data["full_name"] == "Student User"
        assert len(me_data["enrolled_subjects"]) == 7

        # 13. Refresh Token Exchange (HTTP 200)
        res_refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert res_refresh.status_code == 200
        refreshed_tokens = res_refresh.json()
        assert "access_token" in refreshed_tokens
        assert refreshed_tokens["token_type"] == "bearer"

        # 14. Token Version Invalidation Test
        user_repo = UserRepository(db_session)
        identity = await user_repo.get_identity_by_email("student@vit.edu")
        await user_repo.increment_token_version(identity)
        await db_session.commit()

        # Old access token must now be revoked
        res_revoked = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert res_revoked.status_code == 401
        assert "revoked" in res_revoked.json()["message"].lower()

    app.dependency_overrides.clear()
