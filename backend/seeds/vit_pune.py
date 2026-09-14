import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.enums import SubjectType
from app.models.institution import College, Department, Division, Semester, Subject

async def seed_vit_pune_curriculum(db: AsyncSession):
    stmt = select(College).where(College.code == "VIT_PUNE")
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        print("VIT Pune already seeded.")
        return

    college = College(
        name="Vishwakarma Institute of Technology, Pune",
        code="VIT_PUNE",
        city="Pune",
        time_zone="Asia/Kolkata",
        erp_portal_url="https://learner.vit.edu",
    )
    db.add(college)
    await db.flush()

    dept = Department(
        college_id=college.id,
        name="Instrumentation and Control Engineering",
        code="INFT_INST",
    )
    db.add(dept)
    await db.flush()

    sem = Semester(
        department_id=dept.id,
        semester_number=3,
        academic_year="2026-2027",
    )
    db.add(sem)
    await db.flush()

    div = Division(
        semester_id=sem.id,
        name="SEDA - Division D",
    )
    db.add(div)
    await db.flush()

    subjects_data = [
        ("Sensors and Transducers", "IC2303", 4, SubjectType.THEORY),
        ("Data Science", "IC2301", 4, SubjectType.THEORY),
        ("Microcontroller & Applications", "MM1408", 4, SubjectType.THEORY),
        ("Object Oriented Programming", "IC2305", 4, SubjectType.THEORY),
        ("Database Management Systems", "IC2307", 4, SubjectType.THEORY),
        ("Reasoning & Aptitude Development - 3", "HS2001", 2, SubjectType.THEORY),
        ("Design Thinking - 1", "IC2311", 1, SubjectType.PROJECT),
    ]

    for name, code, credits, stype in subjects_data:
        subj = Subject(
            semester_id=sem.id,
            name=name,
            code=code,
            credits=credits,
            subject_type=stype,
        )
        db.add(subj)

    await db.commit()
    print("Seeded VIT Pune curriculum successfully.")

if __name__ == "__main__":
    async def main():
        async with AsyncSessionLocal() as session:
            await seed_vit_pune_curriculum(session)
    asyncio.run(main())
