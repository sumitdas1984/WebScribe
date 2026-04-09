"""
API: Notes Endpoints

GET /v1/notes/{job_id} - List all note versions for a job
PUT /v1/notes/{note_id} - Update a note's content
POST /v1/notes/{note_id}/save - Save note to Knowledge Base
"""

import json
from typing import List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session_dependency
from models import MarkdownNote
from kb.writer import save_to_kb


router = APIRouter(prefix="/v1/notes", tags=["notes"])


class NoteResponse(BaseModel):
    """Response model for a single note"""
    id: str
    job_id: str
    title: str
    content: str
    template_id: str
    tags: List[str]
    version: int
    saved_path: Optional[str]
    created_at: str


class NotesListResponse(BaseModel):
    """Response for GET /v1/notes/{job_id}"""
    notes: List[NoteResponse]


class UpdateNoteRequest(BaseModel):
    """Request body for PUT /v1/notes/{note_id}"""
    title: Optional[str] = None
    content: Optional[str] = None


class SaveNoteResponse(BaseModel):
    """Response for POST /v1/notes/{note_id}/save"""
    note_id: str
    saved_path: str


@router.get("/{job_id}", response_model=NotesListResponse)
def list_notes_for_job(
    job_id: str,
    session: Session = Depends(get_session_dependency)
):
    """
    List all MarkdownNote versions for a job, ordered by creation date descending.

    Returns all note versions associated with the job, newest first.
    Each version represents a different AI synthesis run (with potentially different templates).

    Returns:
    - notes: List of notes with all fields

    Raises:
    - 404: If job_id does not exist or has no notes
    """
    statement = select(MarkdownNote).where(
        MarkdownNote.job_id == job_id
    ).order_by(MarkdownNote.created_at.desc())

    notes = session.exec(statement).all()

    if not notes:
        raise HTTPException(
            status_code=404,
            detail=f"No notes found for job {job_id}"
        )

    # Convert to response model
    note_responses = []
    for note in notes:
        tags = json.loads(note.tags)
        note_responses.append(NoteResponse(
            id=note.id,
            job_id=note.job_id,
            title=note.title,
            content=note.content,
            template_id=note.template_id,
            tags=tags,
            version=note.version,
            saved_path=note.saved_path,
            created_at=note.created_at.isoformat()
        ))

    return NotesListResponse(notes=note_responses)


@router.put("/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: str,
    request: UpdateNoteRequest,
    session: Session = Depends(get_session_dependency)
):
    """
    Update a note's title and/or content.

    Allows editing the AI-generated note before saving to Knowledge Base.

    Request body:
    - title: New title (optional)
    - content: New content (optional)

    Returns:
    - The updated note

    Raises:
    - 404: If note_id does not exist
    """
    note = session.get(MarkdownNote, note_id)

    if not note:
        raise HTTPException(
            status_code=404,
            detail=f"Note {note_id} not found"
        )

    # Update fields
    if request.title is not None:
        note.title = request.title

    if request.content is not None:
        note.content = request.content

    session.add(note)
    session.commit()
    session.refresh(note)

    # Convert to response
    tags = json.loads(note.tags)
    return NoteResponse(
        id=note.id,
        job_id=note.job_id,
        title=note.title,
        content=note.content,
        template_id=note.template_id,
        tags=tags,
        version=note.version,
        saved_path=note.saved_path,
        created_at=note.created_at.isoformat()
    )


@router.post("/{note_id}/save", response_model=SaveNoteResponse)
def save_note_to_kb(
    note_id: str,
    session: Session = Depends(get_session_dependency)
):
    """
    Save a note to the Knowledge Base directory as a .md file.

    Derives the filename from the note's title and handles collision avoidance.
    Updates the note's saved_path field in the database.

    Returns:
    - note_id: The note ID
    - saved_path: Absolute path where the file was saved

    Raises:
    - 404: If note_id does not exist
    """
    note = session.get(MarkdownNote, note_id)

    if not note:
        raise HTTPException(
            status_code=404,
            detail=f"Note {note_id} not found"
        )

    # Save to KB
    saved_path = save_to_kb(note)

    # Update note record with saved path
    note.saved_path = str(saved_path)
    session.add(note)
    session.commit()

    return SaveNoteResponse(
        note_id=note.id,
        saved_path=str(saved_path)
    )
