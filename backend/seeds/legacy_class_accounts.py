import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.enums import EnrollmentStatus, IdentityProvider
from app.models.institution import College, Department, Division, Semester, Subject
from app.models.student import AcademicBrain, Enrollment, Streak, User, UserIdentity


LEGACY_USERS = [
    ('18ab99bc-b006-4442-9120-e0859aa36359', 'ritesh.1262140045@vit.edu', 'Ritesh Malkhan Pawar', '1262140045', 'B1'),
    ('c99f2cea-3b63-42d2-8522-57671c9ed258', 'chetan.1262140046@vit.edu', 'Chetan Sharad Hiwale', '1262140046', 'B1'),
    ('d981af58-de48-4d65-aab3-d7917ce74543', 'swapnil.1262140069@vit.edu', 'Swapnil Vitthal Mehere', '1262140069', 'B1'),
    ('01a4b319-acaa-4bb6-9da7-f48045f8e3cf', 'arya.1262140106@vit.edu', 'Arya Kalpesh Mhaske', '1262140106', 'B1'),
    ('e8a2d0e2-234d-4556-b662-c55e45f0831f', 'anuradha.1262140108@vit.edu', 'Anuradha Anil Rathod', '1262140108', 'B1'),
    ('2470399d-3a61-48c7-998d-40604b2140f0', 'rohit.1262140136@vit.edu', 'Rohit Babu Dhawale', '1262140136', 'B1'),
    ('d5e586e7-b977-4d43-8433-b1bdc4af6c0f', 'samadhan.1262140158@vit.edu', 'Samadhan Mahadeo Molak', '1262140158', 'B1'),
    ('b09be3e4-c8e2-4ca7-abad-cec5f64638db', 'aditya.1262140167@vit.edu', 'Aditya Sandeep Mandhare', '1262140167', 'B1'),
    ('9f57c9ad-0bbf-42de-8b18-8ee7e0843195', 'avinash.1262140171@vit.edu', 'Avinash Manohar Dhumal', '1262140171', 'B1'),
    ('324a2afd-29fe-41bd-8fb9-6a6ab692cbc4', 'vaishnavi.1262140186@vit.edu', 'Vaishnavi Pandurang Nakate', '1262140186', 'B1'),
    ('ee1583af-7fb9-42d2-affd-89f473196083', 'sanika.1262140196@vit.edu', 'Sanika Keshav Mane', '1262140196', 'B1'),
    ('d1080160-5d22-4277-8f1e-caef0abf7009', 'tejaswinee.1262140200@vit.edu', 'Tejaswinee Machhindranath Salunkhe', '1262140200', 'B1'),
    ('8ad3bfe1-99ca-4dd0-9aab-4bee65d9bd18', 'bhavesh.1262140214@vit.edu', 'Bhavesh Haresh Thakur', '1262140214', 'B1'),
    ('66df59b0-d0b1-43da-b38f-52b18ff9bfc4', 'om.1262140215@vit.edu', 'Om Satishkumar Ahire', '1262140215', 'B1'),
    ('3dfdf72a-65dd-4591-aca8-be65bdc338db', 'tanishka.12620242@vit.edu', 'Tanishka Kishor Chaudhari', '12620242', 'B1'),
    ('cbe9fd8b-d03a-4c50-8d05-5c19987ee1fa', 'nagesh.12620259@vit.edu', 'Nagesh Sanjay Shinde', '12620259', 'B1'),
    ('3e210fcc-6ba3-4ef2-b0d1-98a967067329', 'alfiya.12620263@vit.edu', 'Alfiya Zakir Hussain Shaikh', '12620263', 'B1'),
    ('d2f06bc7-54bd-498d-8675-6093c2d9d579', 'perna.12620284@vit.edu', 'Perna Dadasaheb Bhosale', '12620284', 'B2'),
    ('88d79fb5-8a08-43bd-964e-583337a5dc3b', 'shubham.12620320@vit.edu', 'Shubham Suresh Bade', '12620320', 'B2'),
    ('d7222ba6-e225-43be-96a2-69bbce45857c', 'piyush.12620327@vit.edu', 'Piyush Pravin Dhamne', '12620327', 'B2'),
    ('050d8121-ae23-4a68-8cf1-5bf9a8d8a581', 'atharv.12620339@vit.edu', 'Atharv Naresh Kolshikwar', '12620339', 'B2'),
    ('5d5cb714-7d08-4178-916e-1dc935ad39d6', 'namrata.12620349@vit.edu', 'Namrata Rajesh Narayane', '12620349', 'B2'),
    ('3115678a-c7c6-4d87-b827-d7946a1b560b', 'harshdeep.12620374@vit.edu', 'Harshdeep Dinesh Palwekar', '12620374', 'B2'),
    ('cc8e18a3-8c22-4b56-a192-bf502237ae2d', 'ishwari.12620393@vit.edu', 'Ishwari Deepak Jadhav', '12620393', 'B2'),
    ('699f1a27-e5b8-4bcf-b54b-a969173f5925', 'gauri.12620482@vit.edu', 'Gauri Anant Todankar', '12620482', 'B2'),
    ('1384fecd-c1e3-4890-95b6-4453ad7f2198', 'sahil.12620490@vit.edu', 'Sahil Mohan Hokam', '12620490', 'B2'),
    ('d18fd3c6-be46-4d4b-a815-6dc0cb2475e8', 'atharav.12620515@vit.edu', 'Atharav Bhimrao Gore', '12620515', 'B2'),
    ('2bbb757d-a598-4855-8462-f723c3ec3267', 'pranjal.12620535@vit.edu', 'Pranjal Bajirao Salve', '12620535', 'B2'),
    ('ddec3a34-5ee9-41d9-af02-2027d97109de', 'aniket.12620548@vit.edu', 'Aniket Kakasaheb Sonawane', '12620548', 'B2'),
    ('d0032d07-38cf-4e25-9bdb-b69f45eff689', 'sonali.12620554@vit.edu', 'Sonali Ganesh Wable', '12620554', 'B2'),
    ('9158a0b2-b99f-470d-b900-17d8280b923d', 'ashwini.12620563@vit.edu', 'Ashwini Prakash Ghaywat', '12620563', 'B2'),
    ('fc1d3966-5f06-4b21-85a9-6c409d829c39', 'prachi.12620635@vit.edu', 'Prachi Jayant Darokar', '12620635', 'B2'),
    ('f4283078-9c14-44e7-ad46-fda2668283d6', 'mohammad.12620637@vit.edu', 'Mohammad Nihal Azizuddin Shaikh', '12620637', 'B2'),
    ('f67a4bf7-d562-491d-ae17-16aea4e8d48e', 'aachal.12620646@vit.edu', 'Aachal Umeshrao Desmukh', '12620646', 'B2'),
    ('a26e0d2d-a689-4de2-9dac-3fa6d5e35faa', 'supriya.12620652@vit.edu', 'Supriya Babu Kate', '12620652', 'B3'),
    ('27a112df-8ecc-435a-b471-f93d703e9bd4', 'sayali.12620670@vit.edu', 'Sayali Anna Londhe', '12620670', 'B3'),
    ('31c78369-32b7-4f13-a0cb-2e18a27cd76a', 'chetan.12620677@vit.edu', 'Chetan Sharad Patil', '12620677', 'B3'),
    ('0b024476-ba13-4722-b428-27e08c77e66b', 'vaishnavi.12620695@vit.edu', 'Vaishnavi Anil Shimpi', '12620695', 'B3'),
    ('1f1d4835-97fc-4219-ac1d-4bd9a01c6604', 'balika.12620713@vit.edu', 'Balika Pandurang Surwase', '12620713', 'B3'),
    ('1b2cf6d7-31c7-4e7a-9376-6988fcda874a', 'nandini.12620714@vit.edu', 'Nandini Nagnath Birajdar', '12620714', 'B3'),
    ('54ee92ec-daf3-4910-ade7-4abd3797f3a1', 'om.12620715@vit.edu', 'Om Sanjay Pokale', '12620715', 'B3'),
    ('578a7e75-ee39-4bcc-b202-630169ece848', 'soham.12620716@vit.edu', 'Soham Shahaji Patil', '12620716', 'B3'),
    ('6cbc049b-a51e-4056-a66a-99a64d20baa9', 'srushti.12620723@vit.edu', 'Srushti Sachin Dani', '12620723', 'B3'),
    ('4b97f5d4-89c3-45a8-8a04-ac1654b9c0d2', 'aditya.12620724@vit.edu', 'Aditya Vitthal Kale', '12620724', 'B3'),
    ('13164630-6880-4102-9528-643e41c448ef', 'rutuja.12620733@vit.edu', 'Rutuja Vinod Deore', '12620733', 'B3'),
]


async def seed_legacy_class_accounts(db: AsyncSession) -> int:
    division = (await db.execute(select(Division).order_by(Division.id.asc()))).scalars().first()
    if not division:
        raise RuntimeError('VIT Pune division must be seeded before legacy accounts.')

    semester = await db.get(Semester, division.semester_id)
    department = await db.get(Department, semester.department_id)
    college = await db.get(College, department.college_id)
    subjects = (
        await db.execute(
            select(Subject)
            .where(Subject.semester_id == semester.id)
            .order_by(Subject.code.asc())
        )
    ).scalars().all()

    created = 0
    batch_supported = hasattr(User, 'batch')

    for legacy_id, email, full_name, prn, batch in LEGACY_USERS:
        existing_user = (
            await db.execute(select(User).where(User.prn_number == prn))
        ).scalar_one_or_none()
        if existing_user:
            if batch_supported and not getattr(existing_user, 'batch', None):
                existing_user.batch = batch
            continue

        existing_identity = (
            await db.execute(select(UserIdentity).where(UserIdentity.email == email))
        ).scalar_one_or_none()
        if existing_identity:
            continue

        user_kwargs = dict(
            id=uuid.UUID(legacy_id),
            full_name=full_name,
            college_id=college.id,
            department_id=department.id,
            division_id=division.id,
            prn_number=prn,
        )
        if batch_supported:
            user_kwargs['batch'] = batch

        user = User(**user_kwargs)
        user.is_active = True
        db.add(user)
        await db.flush()

        db.add(
            UserIdentity(
                user_id=user.id,
                provider=IdentityProvider.LOCAL,
                provider_user_id=email,
                email=email,
                password_hash=get_password_hash(prn),
                token_version=1,
            )
        )
        db.add(Streak(user_id=user.id, current_streak=0, longest_streak=0))
        db.add(
            AcademicBrain(
                user_id=user.id,
                total_study_minutes=0,
                average_focus_rating=0.0,
                consistency_score=100.0,
                average_quiz_score=0.0,
            )
        )

        for subject in subjects:
            db.add(
                Enrollment(
                    user_id=user.id,
                    subject_id=subject.id,
                    status=EnrollmentStatus.ACTIVE,
                )
            )

        created += 1

    await db.commit()
    print(f'Legacy class accounts ready. Created {created}, total roster {len(LEGACY_USERS)}.')
    return created


if __name__ == '__main__':
    async def main():
        async with AsyncSessionLocal() as session:
            await seed_legacy_class_accounts(session)

    asyncio.run(main())
