import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)
from app.models.institution import College, Department, Division, Semester, Subject
from app.models.student import Enrollment, User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    EnrolledSubjectResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserMeResponse,
)

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    if not validate_password_strength(request.password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password does not meet complexity requirements. Must contain at least 8 characters with uppercase, lowercase, numbers, and symbols.",
        )

    user_repo = UserRepository(db)

    # 1. Unique email check
    existing_identity = await user_repo.get_identity_by_email(request.email)
    if existing_identity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    # 2. Unique PRN check
    if request.prn_number:
        existing_prn = await user_repo.get_user_by_prn(request.prn_number)
        if existing_prn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PRN number already registered.",
            )

    # 3. Hierarchy Validation: college_id must exist
    college_res = await db.execute(select(College).where(College.id == request.college_id))
    college = college_res.scalar_one_or_none()
    if not college:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"College with ID {request.college_id} does not exist.",
        )

    # 4. Hierarchy Validation: department_id must belong to college_id
    dept_res = await db.execute(
        select(Department).where(
            Department.id == request.department_id,
            Department.college_id == request.college_id,
        )
    )
    dept = dept_res.scalar_one_or_none()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department with ID {request.department_id} does not belong to college {request.college_id}.",
        )

    # 5. Hierarchy Validation: division_id must exist
    div_res = await db.execute(select(Division).where(Division.id == request.division_id))
    division = div_res.scalar_one_or_none()
    if not division:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Division with ID {request.division_id} does not exist.",
        )

    # 6. Hierarchy Validation: division must belong to the selected department through its semester
    sem_res = await db.execute(select(Semester).where(Semester.id == division.semester_id))
    semester = sem_res.scalar_one_or_none()
    if not semester or semester.department_id != dept.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected division does not belong to the chosen department or college.",
        )

    # 7. Hierarchy Validation: if semester_id is provided, it must match division.semester_id; else derive it
    if request.semester_id is not None and request.semester_id != division.semester_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provided semester_id {request.semester_id} does not match the division's semester {division.semester_id}.",
        )
    effective_semester_id = division.semester_id

    # 8. Transactional User, Identity, Streak, AcademicBrain, and Subject Auto-Enrollment
    pwd_hash = get_password_hash(request.password)
    user, identity, enrolled_subjects = await user_repo.create_user_with_identity(
        email=request.email,
        password_hash=pwd_hash,
        full_name=request.full_name,
        college_id=request.college_id,
        department_id=request.department_id,
        division_id=request.division_id,
        batch=request.batch,
        semester_id=effective_semester_id,
        prn_number=request.prn_number,
    )
    await db.commit()

    access_token = create_access_token(user.id, identity.id, identity.token_version)
    refresh_token = create_refresh_token(user.id, identity.id, identity.token_version)

    return RegisterResponse(
        id=user.id,
        email=request.email,
        full_name=user.full_name,
        prn_number=user.prn_number,
        college_id=user.college_id,
        department_id=user.department_id,
        division_id=user.division_id,
        batch=user.batch,
        semester_id=effective_semester_id,
        enrolled_subjects=[
            EnrolledSubjectResponse(
                id=s.id,
                name=s.name,
                code=s.code,
                credits=s.credits,
            )
            for s in enrolled_subjects
        ],
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    identifier = str(request.email).strip()
    if '@' in identifier:
        identity = await user_repo.get_identity_by_email(identifier)
    else:
        identity = await user_repo.get_identity_by_prn(identifier)
    if not identity:
        identity = await user_repo.get_identity_by_email(identifier)

    if not identity or not identity.password_hash or not verify_password(request.password, identity.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/PRN or password.",
        )

    access_token = create_access_token(identity.user_id, identity.id, identity.token_version)
    refresh_token = create_refresh_token(identity.user_id, identity.id, identity.token_version)

    identity.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Subject)
        .join(Enrollment, Enrollment.subject_id == Subject.id)
        .where(Enrollment.user_id == current_user.id)
        .order_by(Subject.code.asc())
    )
    res = await db.execute(stmt)
    subjects = res.scalars().all()
    if not subjects and hasattr(current_user, 'enrollments') and current_user.enrollments:
        enrolled_subject_ids = {e.subject_id for e in current_user.enrollments}
        all_subj_res = await db.execute(select(Subject))
        subjects = [s for s in all_subj_res.scalars().all() if s.id in enrolled_subject_ids]

    email = current_user.identities[0].email if current_user.identities else ""

    return UserMeResponse(
        id=current_user.id,
        email=email,
        full_name=current_user.full_name,
        prn_number=current_user.prn_number,
        college_id=current_user.college_id,
        department_id=current_user.department_id,
        division_id=current_user.division_id,
        batch=current_user.batch,
        enrolled_subjects=[
            EnrolledSubjectResponse(
                id=s.id,
                name=s.name,
                code=s.code,
                credits=s.credits,
            )
            for s in subjects
        ],
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_jwt_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type.",
            )
        identity_id = uuid.UUID(payload.get("identity_id"))
        token_version = payload.get("token_version")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    user_repo = UserRepository(db)
    identity = await user_repo.get_identity_by_id(identity_id)
    if not identity or identity.token_version != token_version or not identity.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked or invalidated.",
        )

    new_access_token = create_access_token(identity.user_id, identity.id, identity.token_version)
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=request.refresh_token,
        token_type="bearer",
    )
