from datetime import datetime, time
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


FlightDeckState = Literal[
    "in_class",
    "pre_class",
    "upcoming",
    "post_class",
    "day_complete",
    "schedule_conflict",
]


class FlightDeckClass(BaseModel):
    subject_id: int
    subject_code: str
    subject_name: str
    batch: str
    start_time: time
    end_time: time
    location: str
    instructor_name: Optional[str] = None

    # We do NOT guess syllabus topics.
    # Until a topic is explicitly mapped, this remains null.
    topic: Optional[str] = None


class FlightDeckTodayResponse(BaseModel):
    state: FlightDeckState

    timezone: str
    generated_at: datetime
    batch: str

    current_class: Optional[FlightDeckClass] = None
    next_class: Optional[FlightDeckClass] = None
    previous_class: Optional[FlightDeckClass] = None

    conflicting_classes: List[FlightDeckClass] = Field(default_factory=list)

    minutes_until_next: Optional[int] = None
    minutes_since_previous: Optional[int] = None

    message: str
    