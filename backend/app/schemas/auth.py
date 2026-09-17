import uuid
from typing import List, Optional
from pydantic import BaseModel, Field

try:
    import email_validator
    from pydantic import EmailStr
except ImportError:
    from pydantic import constr
    try:
        EmailStr = constr(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    except TypeError:
        EmailStr = constr(regex=r"^[\w\.-]+@[\w\.-]+\.\w+$")


class SubjectSimpleResponse(BaseModel):
    id: int
    name: str
    code: str
    credits: int

    class Config:
        orm_mode = True
        from_attributes = True


EnrolledSubjectResponse = SubjectSimpleResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=150)
    prn_number: Optional[str] = Field(default=None, max_length=50)
    college_id: int = 1
    department_id: int = 1
    division_id: int = 1
    semester_id: Optional[int] = 1


class LoginRequest(BaseModel):
    email: str = Field(..., description="Student Email Address or PRN Number")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RegisterResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    prn_number: Optional[str] = None
    college_id: int
    department_id: int
    division_id: int
    semester_id: int
    enrolled_subjects: List[EnrolledSubjectResponse] = []
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    class Config:
        orm_mode = True
        from_attributes = True


class UserMeResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    prn_number: Optional[str] = None
    college_id: int
    department_id: int
    division_id: Optional[int] = None
    enrolled_subjects: List[EnrolledSubjectResponse] = []

    class Config:
        orm_mode = True
        from_attributes = True
