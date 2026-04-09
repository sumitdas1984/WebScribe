"""
API: Jobs Endpoints

GET /v1/jobs/{job_id} - Get job status and details
POST /v1/jobs/{job_id}/rerun - Re-run AI synthesis with a different template
"""

import json
from datetime import datetime
from typing import List

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select

from database import get_session_dependency
from models import Job, MarkdownNote, Template
from ai_engine.engine import synthesize


router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


class JobDetailResponse(BaseModel):
    """Response for GET /v1/jobs/{job_id}"""
    job_id: str
    url: str
    status: str
    engine: str
    template_id: str
    logs: List[str]
    created_at: str
    updated_at: str


class RerunRequest(BaseModel):
    """Request body for POST /v1/jobs/{job_id}/rerun"""
    template_id: str


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job_status(
    job_id: str,
    session: Session = Depends(get_session_dependency)
):
    """
    Get the current status and details of a job.

    Returns job metadata including status, logs, and timestamps.
    Used by the UI to poll for job progress.

    Returns:
    - job_id, url, status, engine, template_id
    - logs: List of log messages
    - created_at, updated_at: ISO timestamps

    Raises:
    - 404: If job_id does not exist
    """
    job = session.get(Job, job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    # Parse logs from JSON
    logs = json.loads(job.logs)

    return JobDetailResponse(
        job_id=job.id,
        url=job.url,
        status=job.status.value,
        engine=job.engine,
        template_id=job.template_id,
        logs=logs,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat()
    )


@router.post("/{job_id}/rerun", status_code=200)
async def rerun_ai_synthesis(
    job_id: str,
    request: RerunRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session_dependency)
):
    """
    Re-run AI synthesis on a completed job with a different template.

    Uses the existing scraped content (does NOT re-scrape the URL).
    Creates a new MarkdownNote version linked to the same job.

    Request body:
    - template_id: The template to use for re-synthesis

    Returns:
    - job_id: The job ID
    - message: Success message

    Raises:
    - 404: If job_id does not exist
    - 400: If job has no existing notes (hasn't completed successfully)
    - 404: If template_id does not exist
    """
    # Load job
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    # Get the latest note to extract raw markdown
    # (In a real implementation, we'd store raw_markdown separately)
    statement = select(MarkdownNote).where(
        MarkdownNote.job_id == job_id
    ).order_by(MarkdownNote.created_at.desc())

    existing_notes = session.exec(statement).all()

    if not existing_notes:
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} has no completed notes. Cannot re-run AI synthesis."
        )

    # Load new template
    template = session.get(Template, request.template_id)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Template {request.template_id} not found"
        )

    # Get the most recent note's content as a proxy for raw markdown
    # (This is a simplification - ideally we'd store raw_markdown in the Job record)
    latest_note = existing_notes[0]

    # Calculate next version number
    max_version = max(note.version for note in existing_notes)
    next_version = max_version + 1

    # Enqueue background task to re-synthesize
    async def rerun_synthesis_task():
        # Use the latest note's content as raw markdown
        # In production, we'd store the actual raw_markdown from the de-noiser
        raw_markdown = latest_note.content

        # Synthesize with new template
        new_note = await synthesize(raw_markdown, template, job_id)
        new_note.version = next_version

        session.add(new_note)
        session.commit()

    background_tasks.add_task(rerun_synthesis_task)

    return {
        "job_id": job_id,
        "message": f"Re-running AI synthesis with template '{request.template_id}'"
    }
