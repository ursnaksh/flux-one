import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enums import EnrollmentStatus
from app.models.student import Enrollment, User
from app.schemas.student_content import (
    AssignmentResponse,
    AssignmentSyncRequest,
    AssignmentUpdateRequest,
    NoteResponse,
    NoteSyncItem,
    NoteSyncRequest,
)


router = APIRouter()


async def _active_subject_ids(db: AsyncSession, user_id: uuid.UUID) -> set[int]:
    result = await db.execute(
        select(Enrollment.subject_id).where(
            Enrollment.user_id == user_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    return {int(value) for value in result.scalars().all()}


async def _require_subject_access(db: AsyncSession, user_id: uuid.UUID, subject_id: int) -> None:
    allowed = await _active_subject_ids(db, user_id)
    if subject_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not actively enrolled in that subject.",
        )


async def _list_notes(db: AsyncSession, user_id: uuid.UUID) -> List[NoteResponse]:
    result = await db.execute(
        text(
            """
            SELECT n.id, n.client_id, n.subject_id, s.code AS subject_code,
                   s.name AS subject_name, n.topic, n.title, n.content,
                   n.created_at, n.updated_at
            FROM student_notes n
            JOIN subjects s ON s.id = n.subject_id
            WHERE n.user_id = :user_id
            ORDER BY n.updated_at DESC
            """
        ),
        {"user_id": user_id},
    )
    return [NoteResponse(**dict(row)) for row in result.mappings().all()]


async def _list_assignments(db: AsyncSession, user_id: uuid.UUID) -> List[AssignmentResponse]:
    result = await db.execute(
        text(
            """
            SELECT a.id, a.client_id, a.subject_id, s.code AS subject_code,
                   s.name AS subject_name, a.topic, a.title, a.due_text,
                   a.priority, a.is_done, a.created_at, a.updated_at
            FROM student_assignments a
            JOIN subjects s ON s.id = a.subject_id
            WHERE a.user_id = :user_id
            ORDER BY a.is_done ASC, a.updated_at DESC
            """
        ),
        {"user_id": user_id},
    )
    return [AssignmentResponse(**dict(row)) for row in result.mappings().all()]


@router.get("/notes", response_model=List[NoteResponse])
async def list_notes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _list_notes(db, current_user.id)


@router.post("/notes/sync", response_model=List[NoteResponse])
async def sync_notes(
    request: NoteSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed = await _active_subject_ids(db, current_user.id)
    now = datetime.now(timezone.utc)
    for item in request.items:
        if item.subject_id not in allowed:
            continue
        await db.execute(
            text(
                """
                INSERT INTO student_notes (
                    id, user_id, client_id, subject_id, topic,
                    title, content, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :client_id, :subject_id, :topic,
                    :title, :content, :created_at, :updated_at
                )
                ON CONFLICT (user_id, client_id) DO NOTHING
                """
            ),
            {
                "id": uuid.uuid4(),
                "user_id": current_user.id,
                "client_id": item.client_id,
                "subject_id": item.subject_id,
                "topic": item.topic,
                "title": item.title,
                "content": item.content,
                "created_at": now,
                "updated_at": now,
            },
        )
    await db.commit()
    return await _list_notes(db, current_user.id)


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    request: NoteSyncItem,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_subject_access(db, current_user.id, request.subject_id)
    now = datetime.now(timezone.utc)
    note_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO student_notes (
                id, user_id, client_id, subject_id, topic,
                title, content, created_at, updated_at
            ) VALUES (
                :id, :user_id, :client_id, :subject_id, :topic,
                :title, :content, :created_at, :updated_at
            )
            ON CONFLICT (user_id, client_id) DO UPDATE SET
                subject_id = EXCLUDED.subject_id,
                topic = EXCLUDED.topic,
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                updated_at = EXCLUDED.updated_at
            """
        ),
        {
            "id": note_id,
            "user_id": current_user.id,
            "client_id": request.client_id,
            "subject_id": request.subject_id,
            "topic": request.topic,
            "title": request.title,
            "content": request.content,
            "created_at": now,
            "updated_at": now,
        },
    )
    await db.commit()
    notes = await _list_notes(db, current_user.id)
    return next(note for note in notes if note.client_id == request.client_id)


@router.delete("/notes/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text(
            "DELETE FROM student_notes WHERE user_id = :user_id AND client_id = :client_id"
        ),
        {"user_id": current_user.id, "client_id": client_id},
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Note not found.")


@router.get("/assignments", response_model=List[AssignmentResponse])
async def list_assignments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _list_assignments(db, current_user.id)


@router.post("/assignments/sync", response_model=List[AssignmentResponse])
async def sync_assignments(
    request: AssignmentSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed = await _active_subject_ids(db, current_user.id)
    now = datetime.now(timezone.utc)
    for item in request.items:
        if item.subject_id not in allowed:
            continue
        await db.execute(
            text(
                """
                INSERT INTO student_assignments (
                    id, user_id, client_id, subject_id, topic,
                    title, due_text, priority, is_done, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :client_id, :subject_id, :topic,
                    :title, :due_text, :priority, :is_done, :created_at, :updated_at
                )
                ON CONFLICT (user_id, client_id) DO UPDATE SET
                    subject_id = EXCLUDED.subject_id,
                    topic = EXCLUDED.topic,
                    title = EXCLUDED.title,
                    due_text = EXCLUDED.due_text,
                    priority = EXCLUDED.priority,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "id": uuid.uuid4(),
                "user_id": current_user.id,
                "client_id": item.client_id,
                "subject_id": item.subject_id,
                "topic": item.topic,
                "title": item.title,
                "due_text": item.due_text,
                "priority": item.priority,
                "is_done": item.is_done,
                "created_at": now,
                "updated_at": now,
            },
        )
    await db.commit()
    return await _list_assignments(db, current_user.id)


@router.patch("/assignments/{client_id}", response_model=AssignmentResponse)
async def update_assignment(
    client_id: str,
    request: AssignmentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        text(
            """
            UPDATE student_assignments
            SET is_done = :is_done, updated_at = :updated_at
            WHERE user_id = :user_id AND client_id = :client_id
            """
        ),
        {
            "is_done": request.is_done,
            "updated_at": now,
            "user_id": current_user.id,
            "client_id": client_id,
        },
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    assignments = await _list_assignments(db, current_user.id)
    return next(item for item in assignments if item.client_id == client_id)
