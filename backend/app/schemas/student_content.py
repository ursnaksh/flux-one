import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class NoteSyncItem(BaseModel):
    client_id: str = Field(min_length=1, max_length=80)
    subject_id: int
    topic: Optional[str] = Field(default=None, max_length=300)
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=20000)


class NoteSyncRequest(BaseModel):
    items: List[NoteSyncItem] = Field(default_factory=list, max_length=200)


class NoteResponse(BaseModel):
    id: uuid.UUID
    client_id: str
    subject_id: int
    subject_code: str
    subject_name: str
    topic: Optional[str] = None
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


class AssignmentSyncItem(BaseModel):
    client_id: str = Field(min_length=1, max_length=80)
    subject_id: int
    topic: Optional[str] = Field(default=None, max_length=300)
    title: str = Field(min_length=1, max_length=300)
    due_text: Optional[str] = Field(default=None, max_length=120)
    priority: str = Field(default="med", max_length=20)
    is_done: bool = False


class AssignmentSyncRequest(BaseModel):
    items: List[AssignmentSyncItem] = Field(default_factory=list, max_length=200)


class AssignmentUpdateRequest(BaseModel):
    is_done: bool


class AssignmentResponse(BaseModel):
    id: uuid.UUID
    client_id: str
    subject_id: int
    subject_code: str
    subject_name: str
    topic: Optional[str] = None
    title: str
    due_text: Optional[str] = None
    priority: str
    is_done: bool
    created_at: datetime
    updated_at: datetime
