"""
API: Scrape Endpoint

POST /v1/scrape - Submit URLs for processing
"""

from typing import List
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session

from database import get_session_dependency
from models import Job, JobStatus
from api.validation import validate_urls
from workers.pipeline import run_job


router = APIRouter(prefix="/v1", tags=["scrape"])


class ScrapeRequest(BaseModel):
    """Request body for POST /v1/scrape"""
    urls: List[str]
    engine: str = "static"  # "static" or "dynamic"
    template_id: str = "research-summary"


class JobResponse(BaseModel):
    """Individual job response"""
    job_id: str
    url: str
    status: str


class ScrapeResponse(BaseModel):
    """Response for POST /v1/scrape"""
    jobs: List[JobResponse]


@router.post("/scrape", response_model=ScrapeResponse, status_code=200)
async def scrape_urls(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session_dependency)
):
    """
    Submit one or more URLs for scraping and processing.

    Validates URLs, creates Job records, and enqueues background workers.
    Returns immediately with job IDs - processing happens asynchronously.

    Request body:
    - urls: List of URLs to process
    - engine: "static" (default) or "dynamic"
    - template_id: AI template to use (default: "research-summary")

    Returns:
    - jobs: List of created jobs with job_id, url, and status

    Raises:
    - 422: If any URL is invalid (malformed or non-http/https)
    """
    # Validate all URLs
    validation_errors = validate_urls(request.urls)
    if validation_errors:
        raise HTTPException(
            status_code=422,
            detail=validation_errors
        )

    # Validate engine
    if request.engine not in ["static", "dynamic"]:
        raise HTTPException(
            status_code=422,
            detail=[{"error": f"Invalid engine '{request.engine}'. Must be 'static' or 'dynamic'."}]
        )

    # Create jobs and enqueue workers
    jobs = []

    for url in request.urls:
        # Create job record
        job = Job(
            url=url,
            engine=request.engine,
            template_id=request.template_id,
            status=JobStatus.queued
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        # Enqueue background worker
        background_tasks.add_task(run_job, job.id, session)

        jobs.append(JobResponse(
            job_id=job.id,
            url=job.url,
            status=job.status.value
        ))

    return ScrapeResponse(jobs=jobs)
