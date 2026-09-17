import asyncio
from datetime import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
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


async def seed_vit_pune_curriculum(db: AsyncSession):
    # Check if already seeded
    stmt = select(College).where(College.code == "VIT_PUNE")
    res = await db.execute(stmt)
    existing_college = res.scalar_one_or_none()
    if existing_college:
        print("VIT Pune already seeded.")
        return existing_college

    # 1. College
    college = College(
        name="Vishwakarma Institute of Technology, Pune",
        code="VIT_PUNE",
        city="Pune",
        time_zone="Asia/Kolkata",
        erp_portal_url="https://learner.vit.edu",
    )
    db.add(college)
    await db.flush()

    # 2. Department
    dept = Department(
        college_id=college.id,
        name="Instrumentation and Control Engineering",
        code="INFT_INST",
    )
    db.add(dept)
    await db.flush()

    # 3. Semester 3 (AY 2026-2027)
    sem = Semester(
        department_id=dept.id,
        semester_number=3,
        academic_year="2026-2027",
    )
    db.add(sem)
    await db.flush()

    # 4. Division SEDA - Division D
    div = Division(
        semester_id=sem.id,
        name="SEDA - Division D",
    )
    db.add(div)
    await db.flush()

    # 5. Exact 7 FLUX ONE Core Curriculum Subjects
    subjects_data = [
        ("Sensors and Transducers", "IC2303", 4, SubjectType.THEORY),
        ("Data Science", "IC2301", 4, SubjectType.THEORY),
        ("Microcontroller & Applications", "MM1408", 4, SubjectType.THEORY),
        ("Object Oriented Programming", "IC2305", 4, SubjectType.THEORY),
        ("Database Management Systems", "IC2307", 4, SubjectType.THEORY),
        ("Reasoning & Aptitude Development - 3", "HS2001", 2, SubjectType.THEORY),
        ("Design Thinking - 1", "IC2311", 1, SubjectType.PROJECT),
    ]

    subject_map = {}
    for name, code, credits, stype in subjects_data:
        subj = Subject(
            semester_id=sem.id,
            name=name,
            code=code,
            credits=credits,
            subject_type=stype,
        )
        db.add(subj)
        await db.flush()
        subject_map[code] = subj

    # 6. Official Timetable Slots (Updated SY-D Timetable, W.E.F 06-Jul-2026)
    # Mapping: day_of_week (1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri)
    # B4 mapped to B1, B5 mapped to B2
    timetable_definitions = [
        # Monday (1)
        (1, time(10, 0), time(11, 0), "MM1408", "C204", "Prof. Pramod Kanjalkar (PMK)", "ALL"),
        (1, time(11, 0), time(12, 0), "IC2303", "C204", "Prof. Seema Mashalkar (SSM)", "ALL"),
        (1, time(13, 0), time(15, 0), "IC2301", "C304", "Prof. Rajesh Pashikanti (RP)", "B2"),
        (1, time(15, 0), time(17, 0), "IC2303", "C307", "Prof. Seema Mashalkar (SSM)", "B1"),
        (1, time(15, 0), time(17, 0), "IC2305", "C304", "Prof. Sheetal Katwe (SMK)", "B2"),
        (1, time(15, 0), time(17, 0), "IC2301", "C305", "Prof. Rajesh Pashikanti (RP)", "B3"),
        (1, time(17, 0), time(18, 0), "IC2311", "Dept", "Dr. Jayant Kulkarni (JVK)", "B1"),
        (1, time(17, 0), time(19, 0), "IC2301", "C304", "Prof. Rajesh Pashikanti (RP)", "B1"),
        (1, time(17, 0), time(19, 0), "IC2303", "C307", "Prof. Seema Mashalkar (SSM)", "B2"),

        # Tuesday (2)
        (2, time(10, 0), time(11, 0), "MM1408", "C301", "Prof. Pramod Kanjalkar (PMK)", "ALL"),
        (2, time(11, 0), time(12, 0), "IC2307", "C301", "Prof. Vikas Nandeshwar (VJN)", "ALL"),
        (2, time(13, 0), time(14, 0), "IC2305", "C301", "Prof. Sheetal Katwe (SMK)", "ALL"),

        # Wednesday (3)
        (3, time(11, 0), time(13, 0), "IC2305", "C308", "Prof. Sheetal Katwe (SMK)", "B3"),
        (3, time(13, 0), time(14, 0), "IC2303", "C301", "Prof. Seema Mashalkar (SSM)", "ALL"),
        (3, time(14, 0), time(15, 0), "IC2311", "Dept", "Dr. Jayant Kulkarni (JVK)", "B2"),
        (3, time(15, 0), time(16, 0), "MM1408", "C314", "Prof. Pramod Kanjalkar (PMK)", "B2"),
        (3, time(16, 0), time(18, 0), "IC2307", "C305", "Prof. Vikas Nandeshwar (VJN)", "B3"),

        # Thursday (4)
        (4, time(9, 0), time(11, 0), "IC2305", "C308", "Prof. Sheetal Katwe (SMK)", "B1"),
        (4, time(11, 0), time(12, 0), "MM1408", "C314", "Prof. Pramod Kanjalkar (PMK)", "B1"),
        (4, time(12, 0), time(13, 0), "IC2303", "C204", "Prof. Seema Mashalkar (SSM)", "ALL"),
        (4, time(14, 0), time(15, 0), "IC2301", "C301", "Prof. Rajesh Pashikanti (RP)", "ALL"),
        (4, time(15, 0), time(17, 0), "IC2307", "C305", "Prof. Vikas Nandeshwar (VJN)", "B1"),

        # Friday (5)
        (5, time(10, 0), time(11, 0), "IC2311", "Dept", "Prof. Sandhya Vaibhav Waghmare (SVW)", "B3"),
        (5, time(11, 0), time(12, 0), "HS2001", "C301", "Prof. Manisha Narwane (MPN)", "ALL"),
        (5, time(12, 0), time(13, 0), "IC2307", "C204", "Prof. Vikas Nandeshwar (VJN)", "ALL"),
        (5, time(13, 0), time(14, 0), "IC2305", "C301", "Prof. Sheetal Katwe (SMK)", "ALL"),
        (5, time(14, 0), time(15, 0), "IC2301", "C301", "Prof. Rajesh Pashikanti (RP)", "ALL"),
        (5, time(15, 0), time(17, 0), "IC2307", "C305", "Prof. Vikas Nandeshwar (VJN)", "B2"),
        (5, time(15, 0), time(17, 0), "IC2303", "C307", "Prof. Seema Mashalkar (SSM)", "B3"),
    ]

    for dow, st, et, code, loc, instr, batch in timetable_definitions:
        subj = subject_map[code]
        slot = TimetableSlot(
            semester_id=sem.id,
            division_id=div.id,
            subject_id=subj.id,
            day_of_week=dow,
            start_time=st,
            end_time=et,
            location=loc,
            instructor_name=instr,
        )
        db.add(slot)

    await db.commit()
    print("Seeded VIT Pune curriculum and 29 timetable slots successfully.")
    return college


if __name__ == "__main__":
    async def main():
        async with AsyncSessionLocal() as session:
            await seed_vit_pune_curriculum(session)
    asyncio.run(main())
