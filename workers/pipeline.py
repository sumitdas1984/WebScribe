"""
Background Worker Pipeline

Orchestrates the full job processing pipeline: scraping, de-noising, AI synthesis.
"""

import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from models import Job, JobStatus, MarkdownNote, Template
from scrapers.static_scraper import StaticScraper
from scrapers.dynamic_scraper import DynamicScraper
from scrapers.exceptions import ScraperError, ScraperTimeoutError
from denoiser.cleaner import clean
from denoiser.exceptions import InsufficientContentError
from ai_engine.engine import synthesize
from ai_engine.exceptions import AIEngineError


async def run_job(job_id: str, session: Session):
    """
    Execute the full worker pipeline for a job.

    Pipeline stages:
    1. Load job from database
    2. Update status to 'running'
    3. Scrape URL using selected engine
    4. De-noise HTML to extract clean Markdown
    5. Synthesize structured note using AI
    6. Persist MarkdownNote to database
    7. Update job status to 'done'

    All errors are caught at the top level, logged to job.logs,
    and the job status is set to 'failed'.

    Args:
        job_id: The Job ID to process
        session: SQLModel database session
    """
    try:
        # Load job
        job = session.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found in database")

        # Update status to running
        job.status = JobStatus.running
        job.updated_at = datetime.now(timezone.utc)
        _append_log(job, "Job started")
        session.add(job)
        session.commit()
        session.refresh(job)

        # Stage 1: Scraping
        _append_log(job, f"Scraping URL: {job.url} using {job.engine} engine")
        session.add(job)
        session.commit()

        raw_html = await _scrape_url(job.url, job.engine)
        _append_log(job, f"Successfully scraped {len(raw_html)} bytes")
        session.add(job)
        session.commit()

        # Stage 2: De-noising
        _append_log(job, "De-noising HTML content")
        session.add(job)
        session.commit()

        raw_markdown = clean(raw_html)
        _append_log(job, f"Extracted {len(raw_markdown)} characters of clean Markdown")
        session.add(job)
        session.commit()

        # Stage 3: AI Synthesis
        _append_log(job, "Synthesizing structured note with AI")
        session.add(job)
        session.commit()

        # Load template
        template = session.get(Template, job.template_id)
        if not template:
            raise ValueError(f"Template {job.template_id} not found")

        note = await synthesize(raw_markdown, template, job_id)

        # Stage 4: Persist Note
        session.add(note)
        session.commit()

        _append_log(job, f"Note created: {note.title}")
        session.add(job)
        session.commit()

        # Mark job as done
        job.status = JobStatus.done
        job.updated_at = datetime.now(timezone.utc)
        _append_log(job, "Job completed successfully")
        session.add(job)
        session.commit()

    except ScraperTimeoutError as e:
        # Timeout error from dynamic scraper
        _handle_job_failure(
            job,
            session,
            f"Scraper timeout: {str(e)}"
        )

    except ScraperError as e:
        # Other scraper errors (HTTP errors, network issues)
        _handle_job_failure(
            job,
            session,
            f"Scraper error: {str(e)}"
        )

    except InsufficientContentError as e:
        # De-noiser found insufficient content
        _handle_job_failure(
            job,
            session,
            f"Insufficient content: {str(e)}"
        )

    except AIEngineError as e:
        # AI synthesis failed
        _handle_job_failure(
            job,
            session,
            f"AI synthesis failed: {str(e)}"
        )

    except Exception as e:
        # Catch-all for unexpected errors
        _handle_job_failure(
            job,
            session,
            f"Unexpected error: {str(e)}"
        )


async def _scrape_url(url: str, engine: str) -> str:
    """
    Scrape a URL using the specified engine.

    Args:
        url: The URL to scrape
        engine: Either 'static' or 'dynamic'

    Returns:
        Raw HTML string

    Raises:
        ScraperError: If scraping fails
        ScraperTimeoutError: If dynamic scraper times out
    """
    if engine == "static":
        scraper = StaticScraper()
    elif engine == "dynamic":
        scraper = DynamicScraper()
    else:
        raise ValueError(f"Unknown scraper engine: {engine}")

    result = await scraper.fetch(url)
    return result.raw_html


def _append_log(job: Job, message: str):
    """
    Append a log message to the job's logs.

    Args:
        job: The Job to update
        message: The log message to append
    """
    logs = json.loads(job.logs)
    logs.append(message)
    job.logs = json.dumps(logs)
    job.updated_at = datetime.now(timezone.utc)


def _handle_job_failure(job: Job, session: Session, error_message: str):
    """
    Mark job as failed and log the error.

    Args:
        job: The Job that failed
        session: Database session
        error_message: The error message to log
    """
    try:
        job.status = JobStatus.failed
        job.updated_at = datetime.now(timezone.utc)
        _append_log(job, f"ERROR: {error_message}")
        session.add(job)
        session.commit()
    except Exception as e:
        # Last-ditch effort to log that something went wrong
        print(f"Failed to update job {job.id} with error: {error_message}")
        print(f"Database update also failed: {str(e)}")
