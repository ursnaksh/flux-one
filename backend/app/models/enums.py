from enum import Enum


class SubjectType(str, Enum):
    THEORY = "THEORY"
    LAB = "LAB"
    SEMINAR = "SEMINAR"
    PROJECT = "PROJECT"


class IdentityProvider(str, Enum):
    LOCAL = "LOCAL"
    GOOGLE = "GOOGLE"


class EnrollmentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DROPPED = "DROPPED"
    COMPLETED = "COMPLETED"


class SessionStatus(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class SessionSource(str, Enum):
    MANUAL = "MANUAL"
    MOBILE = "MOBILE"
    ESP32 = "ESP32"
    API = "API"
