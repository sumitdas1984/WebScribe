"""
Integration Tests: Full Pipeline

Tests the complete end-to-end workflow from URL submission to note generation.
Validates: Requirements 4.5, 9.1, 9.3
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

from main import app
from models import Job, JobStatus, MarkdownNote, SQLModel, Template
from database import get_session_dependency
from scrapers.base import ScraperResult


# Test database setup
@pytest.fixture
def test_db():
    """Create a temporary test database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db_path = Path(tmp.name)

    test_db_url = f"sqlite:///{tmp_db_path}"
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})

    # Create tables
    SQLModel.metadata.create_all(test_engine)

    # Seed test template
    with Session(test_engine) as session:
        template = Template(
            id="test-template",
            name="Test Template",
            prompt_template="Test: {{ raw_markdown }}"
        )
        session.add(template)
        session.commit()

    yield test_engine, tmp_db_path

    # Cleanup
    test_engine.dispose()
    if tmp_db_path.exists():
        tmp_db_path.unlink()


@pytest.fixture
def test_client(test_db):
    """Create a test client with test database"""
    test_engine, tmp_db_path = test_db

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session_dependency] = override_get_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# Integration Test 1: Full Pipeline Smoke Test
@pytest.mark.asyncio
async def test_full_pipeline_with_mocked_dependencies(test_client):
    """
    Property: Full pipeline from URL submission to note generation completes successfully.

    Validates: Requirements 4.5, 9.1

    Tests the complete workflow:
    1. Submit URL via API
    2. Job is created and processed by worker
    3. Scraper fetches content
    4. De-noiser cleans HTML
    5. AI generates structured note
    6. Note is persisted to database
    """
    # Mock scraper to return test HTML
    mock_html = """
    <html>
        <body>
            <main>
                <h1>Test Article</h1>
                <p>This is a test article with enough content to pass validation.
                The content needs to be at least 50 characters long to satisfy
                the minimum content length requirement in the de-noiser.</p>
            </main>
        </body>
    </html>
    """

    mock_scraper_result = ScraperResult(
        raw_html=mock_html,
        final_url="https://example.com",
        status_code=200
    )

    # Mock AI response
    mock_ai_response = MagicMock()
    mock_ai_response.choices = [MagicMock()]
    mock_ai_response.choices[0].message.content = """# Test Article

## Summary
This is a test article.

## Key Concepts
- Testing
- Integration

Tags: test, integration"""

    with patch("workers.pipeline.StaticScraper") as MockScraper, \
         patch("ai_engine.engine.client") as mock_ai_client:

        # Configure mocks
        mock_instance = MockScraper.return_value
        mock_instance.fetch = AsyncMock(return_value=mock_scraper_result)
        mock_ai_client.chat.completions.create = AsyncMock(return_value=mock_ai_response)

        # Submit URL
        response = test_client.post(
            "/v1/scrape",
            json={
                "urls": ["https://example.com"],
                "engine": "static",
                "template_id": "test-template"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1

        job_id = data["jobs"][0]["job_id"]
        assert data["jobs"][0]["status"] == "queued"

        # Wait for background task to complete
        # In a real scenario, the background task runs immediately
        # For testing, we need to give it time to execute
        max_wait = 10  # seconds
        start_time = time.time()

        while time.time() - start_time < max_wait:
            job_response = test_client.get(f"/v1/jobs/{job_id}")
            job_data = job_response.json()

            if job_data["status"] in ["done", "failed"]:
                break

            await asyncio.sleep(0.5)

        # Verify job completed
        job_response = test_client.get(f"/v1/jobs/{job_id}")
        assert job_response.status_code == 200
        job_data = job_response.json()

        assert job_data["status"] == "done", f"Job failed with logs: {job_data.get('logs')}"
        assert "Scraping" in " ".join(job_data["logs"])
        assert "De-noising" in " ".join(job_data["logs"])
        assert "Synthesizing" in " ".join(job_data["logs"])

        # Verify note was created
        notes_response = test_client.get(f"/v1/notes/{job_id}")
        assert notes_response.status_code == 200
        notes_data = notes_response.json()

        assert len(notes_data["notes"]) == 1
        note = notes_data["notes"][0]

        assert note["title"] == "Test Article"
        assert "test" in [tag.lower() for tag in note["tags"]]
        assert note["version"] == 1


# Integration Test 2: Error Handling in Pipeline
@pytest.mark.asyncio
async def test_pipeline_handles_scraper_errors_gracefully(test_client):
    """
    Property: Pipeline handles scraper errors and marks job as failed.

    Validates: Requirements 2.6, 9.1
    """
    from scrapers.exceptions import ScraperError

    with patch("workers.pipeline.StaticScraper") as MockScraper:
        # Configure mock to raise error
        mock_instance = MockScraper.return_value
        mock_instance.fetch = AsyncMock(side_effect=ScraperError("Network error"))

        # Submit URL
        response = test_client.post(
            "/v1/scrape",
            json={
                "urls": ["https://example.com"],
                "engine": "static",
                "template_id": "test-template"
            }
        )

        job_id = response.json()["jobs"][0]["job_id"]

        # Wait for job to process
        max_wait = 5
        start_time = time.time()

        while time.time() - start_time < max_wait:
            job_response = test_client.get(f"/v1/jobs/{job_id}")
            job_data = job_response.json()

            if job_data["status"] == "failed":
                break

            await asyncio.sleep(0.5)

        # Verify job failed
        job_response = test_client.get(f"/v1/jobs/{job_id}")
        job_data = job_response.json()

        assert job_data["status"] == "failed"
        assert any("error" in log.lower() for log in job_data["logs"])


# Integration Test 3: Pipeline with Insufficient Content
@pytest.mark.asyncio
async def test_pipeline_fails_with_insufficient_content(test_client):
    """
    Property: Pipeline fails gracefully when de-noiser finds insufficient content.

    Validates: Requirements 3.5, 9.1
    """
    # Mock scraper to return HTML with very little content
    mock_html = "<html><body><p>Hi</p></body></html>"

    mock_scraper_result = ScraperResult(
        raw_html=mock_html,
        final_url="https://example.com",
        status_code=200
    )

    with patch("workers.pipeline.StaticScraper") as MockScraper:
        mock_instance = MockScraper.return_value
        mock_instance.fetch = AsyncMock(return_value=mock_scraper_result)

        # Submit URL
        response = test_client.post(
            "/v1/scrape",
            json={
                "urls": ["https://example.com"],
                "engine": "static",
                "template_id": "test-template"
            }
        )

        job_id = response.json()["jobs"][0]["job_id"]

        # Wait for job to process
        max_wait = 5
        start_time = time.time()

        while time.time() - start_time < max_wait:
            job_response = test_client.get(f"/v1/jobs/{job_id}")
            job_data = job_response.json()

            if job_data["status"] == "failed":
                break

            await asyncio.sleep(0.5)

        # Verify job failed with insufficient content error
        job_response = test_client.get(f"/v1/jobs/{job_id}")
        job_data = job_response.json()

        assert job_data["status"] == "failed"
        assert any("insufficient content" in log.lower() for log in job_data["logs"])


# Integration Test 4: Concurrent Job Processing
@pytest.mark.asyncio
async def test_concurrent_job_processing(test_client):
    """
    Property: System can process multiple jobs concurrently without degrading response times.

    Validates: Requirements 9.3

    Submits 5 concurrent jobs and verifies:
    - All jobs are created
    - Status check requests respond within 500ms
    - All jobs eventually complete
    """
    # Mock scraper and AI
    mock_html = """
    <html><body><main>
        <h1>Test</h1>
        <p>This is test content with enough text to pass validation requirements.
        We need at least fifty characters here for the de-noiser to accept it.</p>
    </main></body></html>
    """

    mock_scraper_result = ScraperResult(
        raw_html=mock_html,
        final_url="https://example.com",
        status_code=200
    )

    mock_ai_response = MagicMock()
    mock_ai_response.choices = [MagicMock()]
    mock_ai_response.choices[0].message.content = "# Test\n\nContent\n\nTags: test"

    with patch("workers.pipeline.StaticScraper") as MockScraper, \
         patch("ai_engine.engine.client") as mock_ai_client:

        mock_instance = MockScraper.return_value
        mock_instance.fetch = AsyncMock(return_value=mock_scraper_result)
        mock_ai_client.chat.completions.create = AsyncMock(return_value=mock_ai_response)

        # Submit 5 jobs concurrently
        num_jobs = 5
        job_ids = []

        for i in range(num_jobs):
            response = test_client.post(
                "/v1/scrape",
                json={
                    "urls": [f"https://example.com/page{i}"],
                    "engine": "static",
                    "template_id": "test-template"
                }
            )
            assert response.status_code == 200
            job_ids.append(response.json()["jobs"][0]["job_id"])

        # Verify all status checks respond within 500ms
        for job_id in job_ids:
            start_time = time.time()
            response = test_client.get(f"/v1/jobs/{job_id}")
            elapsed_ms = (time.time() - start_time) * 1000

            assert response.status_code == 200
            assert elapsed_ms < 500, f"Status check took {elapsed_ms}ms (should be < 500ms)"

        # Wait for all jobs to complete
        max_wait = 15  # seconds
        start_time = time.time()
        completed_jobs = set()

        while time.time() - start_time < max_wait and len(completed_jobs) < num_jobs:
            for job_id in job_ids:
                if job_id in completed_jobs:
                    continue

                response = test_client.get(f"/v1/jobs/{job_id}")
                job_data = response.json()

                if job_data["status"] in ["done", "failed"]:
                    completed_jobs.add(job_id)

            await asyncio.sleep(0.5)

        # Verify all jobs completed
        assert len(completed_jobs) == num_jobs, f"Only {len(completed_jobs)}/{num_jobs} jobs completed"


# Integration Test 5: Note Update and Save to KB
@pytest.mark.asyncio
async def test_note_update_and_save_to_kb(test_client, test_db):
    """
    Property: Notes can be updated and saved to Knowledge Base.

    Validates: Requirements 6.3, 6.4, 8.1, 8.2
    """
    test_engine, _ = test_db

    with tempfile.TemporaryDirectory() as tmpdir:
        kb_dir = Path(tmpdir)

        # Create a completed job with a note manually
        with Session(test_engine) as session:
            # Create job
            job = Job(
                url="https://example.com",
                engine="static",
                template_id="test-template",
                status=JobStatus.done
            )
            session.add(job)
            session.commit()
            session.refresh(job)

            # Create note
            note = MarkdownNote(
                job_id=job.id,
                title="Original Title",
                content="# Original Title\n\nOriginal content",
                template_id="test-template",
                tags='["test"]',
                version=1
            )
            session.add(note)
            session.commit()
            session.refresh(note)

            note_id = note.id

        # Update note
        update_response = test_client.put(
            f"/v1/notes/{note_id}",
            json={
                "title": "Updated Title",
                "content": "# Updated Title\n\nUpdated content"
            }
        )

        assert update_response.status_code == 200
        updated_note = update_response.json()
        assert updated_note["title"] == "Updated Title"
        assert "Updated content" in updated_note["content"]

        # Save to KB
        with patch("kb.writer.KB_DIR", kb_dir):
            save_response = test_client.post(f"/v1/notes/{note_id}/save")

        assert save_response.status_code == 200
        save_data = save_response.json()

        # Verify file was created
        saved_path = Path(save_data["saved_path"])
        assert saved_path.exists()

        # Verify content matches
        saved_content = saved_path.read_text(encoding="utf-8")
        assert "Updated Title" in saved_content
        assert "Updated content" in saved_content


# Integration Test 6: Job Re-run with Different Template
@pytest.mark.asyncio
async def test_job_rerun_with_different_template(test_client, test_db):
    """
    Property: Re-running a job creates a new note version without re-scraping.

    Validates: Requirements 7.2, 7.3
    """
    test_engine, _ = test_db

    # Create a completed job with a note
    mock_html = """
    <html><body><main>
        <h1>Test Article</h1>
        <p>This is test content with sufficient length for validation purposes.
        We need at least fifty characters to pass the de-noiser requirements.</p>
    </main></body></html>
    """

    mock_scraper_result = ScraperResult(
        raw_html=mock_html,
        final_url="https://example.com",
        status_code=200
    )

    mock_ai_response = MagicMock()
    mock_ai_response.choices = [MagicMock()]
    mock_ai_response.choices[0].message.content = "# Test\n\nContent\n\nTags: test"

    with patch("workers.pipeline.StaticScraper") as MockScraper, \
         patch("ai_engine.engine.client") as mock_ai_client:

        mock_instance = MockScraper.return_value
        mock_instance.fetch = AsyncMock(return_value=mock_scraper_result)
        mock_ai_client.chat.completions.create = AsyncMock(return_value=mock_ai_response)

        # Submit initial job
        response = test_client.post(
            "/v1/scrape",
            json={
                "urls": ["https://example.com"],
                "engine": "static",
                "template_id": "test-template"
            }
        )

        job_id = response.json()["jobs"][0]["job_id"]

        # Wait for job to complete
        max_wait = 10
        start_time = time.time()

        while time.time() - start_time < max_wait:
            job_response = test_client.get(f"/v1/jobs/{job_id}")
            if job_response.json()["status"] == "done":
                break
            await asyncio.sleep(0.5)

        # Verify initial note exists
        notes_response = test_client.get(f"/v1/notes/{job_id}")
        initial_notes = notes_response.json()["notes"]
        assert len(initial_notes) == 1
        assert initial_notes[0]["version"] == 1

        # Record scraper call count
        initial_scraper_calls = mock_instance.fetch.call_count

        # Re-run with different template
        # Note: We need to create a second template first
        with Session(test_engine) as session:
            template2 = Template(
                id="test-template-2",
                name="Test Template 2",
                prompt_template="Test2: {{ raw_markdown }}"
            )
            session.add(template2)
            session.commit()

        rerun_response = test_client.post(
            f"/v1/jobs/{job_id}/rerun",
            json={"template_id": "test-template-2"}
        )

        assert rerun_response.status_code == 200

        # Wait for re-run to complete
        await asyncio.sleep(2)

        # Verify scraper was NOT called again
        final_scraper_calls = mock_instance.fetch.call_count
        assert final_scraper_calls == initial_scraper_calls, \
            "Scraper should not be called on re-run"

        # Verify second note version exists
        notes_response = test_client.get(f"/v1/notes/{job_id}")
        final_notes = notes_response.json()["notes"]

        assert len(final_notes) == 2, "Should have 2 note versions"

        versions = [note["version"] for note in final_notes]
        assert 1 in versions and 2 in versions


# Integration Test 7: Invalid URL Validation
def test_invalid_url_returns_422(test_client):
    """
    Property: Invalid URLs return 422 with descriptive error messages.

    Validates: Requirements 1.3
    """
    response = test_client.post(
        "/v1/scrape",
        json={
            "urls": ["ftp://invalid.com", "not-a-url"],
            "engine": "static",
            "template_id": "test-template"
        }
    )

    assert response.status_code == 422
    detail = response.json()["detail"]

    assert len(detail) == 2
    assert any("ftp://invalid.com" in str(err) for err in detail)
    assert any("not-a-url" in str(err) for err in detail)
