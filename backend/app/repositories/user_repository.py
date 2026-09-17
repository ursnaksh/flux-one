import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import EnrollmentStatus, IdentityProvider
from app.models.institution import Division, Subject
from app.models.student import AcademicBrain, Enrollment, Streak, User, UserIdentity


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.identities),
                selectinload(User.enrollments),
                selectinload(User.streak),
                selectinload(User.academic_brain),
            )
        )
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()
        return user

    async def get_user_by_prn(self, prn: str) -> Optional[User]:
        stmt = select(User).where(User.prn_number == prn)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_identity_by_id(self, identity_id: uuid.UUID) -> Optional[UserIdentity]:
        stmt = (
            select(UserIdentity)
            .where(UserIdentity.id == identity_id)
            .options(
                selectinload(UserIdentity.user).selectinload(User.enrollments),
                selectinload(UserIdentity.user).selectinload(User.streak),
                selectinload(UserIdentity.user).selectinload(User.academic_brain),
            )
        )
        res = await self.db.execute(stmt)
        identity = res.scalar_one_or_none()
        if identity and (not hasattr(identity, "user") or isinstance(identity.user, type) or getattr(identity, "user", None) is None or not hasattr(identity.user, "is_active")):
            identity.user = await self.get_user_by_id(identity.user_id)
        return identity

    async def get_identity_by_email(self, email: str) -> Optional[UserIdentity]:
        stmt = (
            select(UserIdentity)
            .where(UserIdentity.email == email)
            .options(
                selectinload(UserIdentity.user).selectinload(User.enrollments),
                selectinload(UserIdentity.user).selectinload(User.streak),
                selectinload(UserIdentity.user).selectinload(User.academic_brain),
            )
        )
        res = await self.db.execute(stmt)
        identity = res.scalar_one_or_none()
        if identity and (not hasattr(identity, "user") or isinstance(identity.user, type) or getattr(identity, "user", None) is None or not hasattr(identity.user, "is_active")):
            identity.user = await self.get_user_by_id(identity.user_id)
        return identity

    async def get_identity_by_prn(self, prn: str) -> Optional[UserIdentity]:
        user = await self.get_user_by_prn(prn)
        if not user:
            return None
        stmt = (
            select(UserIdentity)
            .where(UserIdentity.user_id == user.id)
            .options(
                selectinload(UserIdentity.user).selectinload(User.enrollments),
                selectinload(UserIdentity.user).selectinload(User.streak),
                selectinload(UserIdentity.user).selectinload(User.academic_brain),
            )
        )
        res = await self.db.execute(stmt)
        identity = res.scalar_one_or_none()
        if identity and (not hasattr(identity, "user") or getattr(identity, "user", None) is None):
            identity.user = user
        return identity

    async def increment_token_version(self, identity: UserIdentity) -> None:
        identity.token_version += 1
        await self.db.flush()

    async def create_user_with_identity(
        self,
        email: str,
        password_hash: str,
        full_name: str,
        college_id: int,
        department_id: int,
        division_id: int,
        semester_id: int,
        prn_number: Optional[str] = None,
    ) -> Tuple[User, UserIdentity, List[Subject]]:
        user = User(
            full_name=full_name,
            college_id=college_id,
            department_id=department_id,
            division_id=division_id,
            prn_number=prn_number,
        )
        user.is_active = True
        self.db.add(user)
        await self.db.flush()

        identity = UserIdentity(
            user_id=user.id,
            provider=IdentityProvider.LOCAL,
            provider_user_id=email,
            email=email,
            password_hash=password_hash,
            token_version=1,
        )
        identity.user = user
        user.identities = [identity]
        self.db.add(identity)

        streak = Streak(
            user_id=user.id,
            current_streak=0,
            longest_streak=0,
        )
        user.streak = streak
        self.db.add(streak)

        brain = AcademicBrain(
            user_id=user.id,
            total_study_minutes=0,
            average_focus_rating=0.0,
            consistency_score=100.0,
            average_quiz_score=0.0,
        )
        user.academic_brain = brain
        self.db.add(brain)

        # Auto-enroll in all active subjects for the division's semester
        subj_stmt = (
            select(Subject)
            .where(Subject.semester_id == semester_id)
            .order_by(Subject.code.asc())
        )
        subj_res = await self.db.execute(subj_stmt)
        subjects = subj_res.scalars().all()

        enrolled_subjects = []
        user_enrollments = []
        for sub in subjects:
            enrollment = Enrollment(
                user_id=user.id,
                subject_id=sub.id,
                status=EnrollmentStatus.ACTIVE,
            )
            self.db.add(enrollment)
            enrolled_subjects.append(sub)
            user_enrollments.append(enrollment)

        user.enrollments = user_enrollments
        await self.db.flush()
        return user, identity, enrolled_subjects
