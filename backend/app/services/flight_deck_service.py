from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import EnrollmentStatus
from app.models.institution import TimetableSlot
from app.models.student import Enrollment, User
from app.schemas.flight_deck import FlightDeckClass, FlightDeckTodayResponse


IST = ZoneInfo("Asia/Kolkata")


def _slot_response(slot: TimetableSlot) -> FlightDeckClass:
    return FlightDeckClass(
        subject_id=slot.subject_id,
        subject_code=slot.subject.code,
        subject_name=slot.subject.name,
        batch=slot.batch,
        start_time=slot.start_time,
        end_time=slot.end_time,
        location=slot.location,
        instructor_name=slot.instructor_name,
        topic=None,
    )


def _find_schedule_conflict(slots):
    for index, first in enumerate(slots):
        for second in slots[index + 1:]:
            if (
                first.start_time < second.end_time
                and second.start_time < first.end_time
            ):
                return [first, second]

    return []


async def get_today_flight_deck(
    db: AsyncSession,
    user: User,
) -> FlightDeckTodayResponse:

    if user.division_id is None:
        raise ValueError(
            "Your division is not configured. Flight Deck cannot determine your timetable."
        )

    if not user.batch:
        raise ValueError(
            "Your batch is not configured. Select B1, B2, or B3 before using Flight Deck."
        )

    now = datetime.now(IST)
    day_of_week = now.isoweekday()

    stmt = (
        select(TimetableSlot)
        .join(Enrollment, Enrollment.subject_id == TimetableSlot.subject_id)
        .options(selectinload(TimetableSlot.subject))
        .where(
            Enrollment.user_id == user.id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
            TimetableSlot.division_id == user.division_id,
            TimetableSlot.day_of_week == day_of_week,
            TimetableSlot.batch.in_(["ALL", user.batch]),
        )
        .order_by(
            TimetableSlot.start_time.asc(),
            TimetableSlot.end_time.asc(),
        )
    )

    result = await db.execute(stmt)
    slots = list(result.scalars().all())

    conflict = _find_schedule_conflict(slots)

    if conflict:
        return FlightDeckTodayResponse(
            state="schedule_conflict",
            timezone="Asia/Kolkata",
            generated_at=now,
            batch=user.batch,
            conflicting_classes=[
                _slot_response(slot)
                for slot in conflict
            ],
            message=(
                "FLUX ONE found overlapping timetable entries for your batch. "
                "The timetable must be verified before choosing a class."
            ),
        )

    current_slot = None
    previous_slot = None
    next_slot = None

    previous_end = None
    next_start = None

    for slot in slots:
        start_dt = datetime.combine(
            now.date(),
            slot.start_time,
            tzinfo=IST,
        )

        end_dt = datetime.combine(
            now.date(),
            slot.end_time,
            tzinfo=IST,
        )

        if start_dt <= now < end_dt:
            current_slot = slot

        elif end_dt <= now:
            if previous_end is None or end_dt > previous_end:
                previous_slot = slot
                previous_end = end_dt

        elif start_dt > now:
            if next_start is None or start_dt < next_start:
                next_slot = slot
                next_start = start_dt

    minutes_until_next = None
    if next_start is not None:
        minutes_until_next = max(
            0,
            int((next_start - now).total_seconds() // 60),
        )

    minutes_since_previous = None
    if previous_end is not None:
        minutes_since_previous = max(
            0,
            int((now - previous_end).total_seconds() // 60),
        )

    if current_slot is not None:
        state = "in_class"
        message = (
            f"You are currently in "
            f"{current_slot.subject.code} - "
            f"{current_slot.subject.name}."
        )

    elif next_slot is not None and minutes_until_next is not None and minutes_until_next <= 45:
        state = "pre_class"
        message = (
            f"{next_slot.subject.code} starts in "
            f"{minutes_until_next} minutes at "
            f"{next_slot.location}."
        )

    elif previous_slot is not None and minutes_since_previous is not None and minutes_since_previous <= 45:
        state = "post_class"
        message = (
            f"{previous_slot.subject.code} just finished. "
            f"This is a good time to capture notes and review."
        )

    elif next_slot is not None:
        state = "upcoming"
        message = (
            f"Your next class is "
            f"{next_slot.subject.code} at "
            f"{next_slot.start_time.strftime('%H:%M')}."
        )

    else:
        state = "day_complete"
        message = "No more classes are scheduled for today."

    return FlightDeckTodayResponse(
        state=state,
        timezone="Asia/Kolkata",
        generated_at=now,
        batch=user.batch,
        current_class=(
            _slot_response(current_slot)
            if current_slot
            else None
        ),
        next_class=(
            _slot_response(next_slot)
            if next_slot
            else None
        ),
        previous_class=(
            _slot_response(previous_slot)
            if previous_slot
            else None
        ),
        minutes_until_next=minutes_until_next,
        minutes_since_previous=minutes_since_previous,
        message=message,
    )
