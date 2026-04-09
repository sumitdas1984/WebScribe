# Implementation Plan: WebScribe

## Overview

Implement WebScribe incrementally: project scaffold → data models → worker pipeline components → API layer → Streamlit frontend. Each task wires into the previous, ending with a fully integrated system.

## Tasks

- [ ] 1. Project scaffold and configuration
  - Create the package directory structure: `api/`, `workers/`, `scrapers/`, `denoiser/`, `ai_engine/`, `kb/`, `ui/`, `tests/unit/`, `tests/api/`, `tests/integration/`
  - Update `pyproject.toml` with all dependencies: `fastapi`, `uvicorn`, `sqlmodel`, `httpx`, `beautifulsoup4`, `lxml`, `markdownify`, `playwright`, `openai`, `streamlit`, `hypothesis`, `pytest`, `pytest-asyncio`
  - Add `__init__.py` to each package directory
  - Create `config.py` at the project root with settings for `DATABASE_URL`, `KB_DIR`, and `LLM_BASE_URL` read from environment variables
  - _Requirements: 10.1_

- [ ] 2. Data models and database initialization
  - [ ] 2.1 Implement `JobStatus` enum and `Job`, `MarkdownNote`, `Template` SQLModel table models in `models.py`
    - Include all fields from the design: `Job` (id, url, engine, template_id, status, logs as JSON string, created_at, updated_at), `MarkdownNote` (id, job_id FK, title, content, template_id, tags as JSON string, version, saved_path, created_at), `Template` (id, name, prompt_template, created_at, updated_at)
    - _Requirements: 10.1_
  - [ ] 2.2 Implement `database.py` with `create_db_and_tables()` and a `get_session()` dependency
    - Call `SQLModel.metadata.create_all(engine)` on startup
    - Seed three default `Template` rows if the table is empty: "Research Summary", "Beginner Explainer", "API Endpoint Extractor"
    - _Requirements: 10.2_
  - [ ] 2.3 Write integration test for DB initialization
    - Assert that starting the app with no DB file creates the schema and seeds templates
    - _Requirements: 10.2_

- [ ] 3. Scraper engine
  - [ ] 3.1 Implement `scrapers/base.py` with `ScraperResult` dataclass and `BaseScraper` ABC
    - Fields: `raw_html: str`, `final_url: str`, `status_code: int`
    - _Requirements: 2.1_
  - [ ] 3.2 Implement `scrapers/static_scraper.py` — `StaticScraper(BaseScraper)`
    - Use `httpx.AsyncClient` to GET the URL; raise `ScraperError` on 4xx/5xx
    - _Requirements: 2.2, 2.4_
  - [ ] 3.3 Implement `scrapers/dynamic_scraper.py` — `DynamicScraper(BaseScraper)`
    - Run Playwright in a subprocess via `asyncio.to_thread`; wait for `networkidle`; enforce 30-second timeout; raise `ScraperTimeoutError` on breach
    - _Requirements: 2.3, 2.5, 2.6_
  - [ ] 3.4 Implement `scrapers/exceptions.py` with `ScraperError` and `ScraperTimeoutError`
    - _Requirements: 2.6_
  - [ ] 3.5 Write property test for engine routing (Property 2)
    - **Property 2: Engine Routing**
    - **Validates: Requirements 2.2, 2.3**
  - [ ] 3.6 Write property test for dynamic scraper timeout (Property 3)
    - **Property 3: Dynamic Scraper Timeout Produces Failed Job**
    - **Validates: Requirements 2.6**

- [ ] 4. De-noiser
  - [ ] 4.1 Implement `denoiser/cleaner.py` — `clean(raw_html: str) -> str`
    - Parse with BeautifulSoup (`lxml`); select `<main>` or `<article>`, fall back to `<body>`; decompose `<header>`, `<footer>`, `<nav>`, `<aside>`, `<script>`, `<style>`; convert with `markdownify`; collapse 3+ blank lines; strip whitespace
    - Raise `InsufficientContentError` if result is fewer than 50 characters
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [ ] 4.2 Implement `denoiser/exceptions.py` with `InsufficientContentError`
    - _Requirements: 3.5_
  - [ ] 4.3 Write property test for content extraction with fallback (Property 4)
    - **Property 4: Content Extraction with Fallback**
    - **Validates: Requirements 3.1, 3.2**
  - [ ] 4.4 Write property test for noise element removal (Property 5)
    - **Property 5: Noise Element Removal**
    - **Validates: Requirements 3.3**
  - [ ] 4.5 Write property test for Markdown structure preservation (Property 6)
    - **Property 6: Markdown Structure Preservation**
    - **Validates: Requirements 3.4**

- [ ] 5. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. AI synthesis engine
  - [ ] 6.1 Implement `ai_engine/engine.py` — `async def synthesize(raw_markdown: str, template: Template) -> MarkdownNote`
    - Build prompt by injecting `raw_markdown` into `template.prompt_template`
    - Call OpenAI-compatible API; parse response into `MarkdownNote` fields (title, content, tags)
    - Retry up to 3 times with exponential backoff (1s, 2s, 4s); raise `AIEngineError` after exhausting retries
    - _Requirements: 4.2, 4.3, 4.4_
  - [ ] 6.2 Implement `ai_engine/exceptions.py` with `AIEngineError`
    - _Requirements: 4.4_
  - [ ] 6.3 Write property test for AI engine prompt construction (Property 7)
    - **Property 7: AI Engine Receives Content and Template**
    - **Validates: Requirements 4.2**
  - [ ] 6.4 Write property test for MarkdownNote required fields (Property 8)
    - **Property 8: MarkdownNote Has All Required Fields**
    - **Validates: Requirements 4.3**
  - [ ] 6.5 Write property test for LLM retry count (Property 9)
    - **Property 9: LLM Retry Count**
    - **Validates: Requirements 4.4**

- [ ] 7. Knowledge base file writer
  - [ ] 7.1 Implement `kb/writer.py` — `save_to_kb(note: MarkdownNote, kb_dir: Path) -> Path`
    - Derive slug: lowercase, replace non-`[a-z0-9]` with `-`, collapse consecutive hyphens, strip leading/trailing hyphens, append `.md`
    - Append `-2`, `-3`, etc. if file exists; write atomically (write to `.tmp`, then `rename`)
    - Return the final `Path`
    - _Requirements: 8.2, 8.3, 8.4_
  - [ ] 7.2 Write property test for KB file content matches note (Property 20)
    - **Property 20: KB File Content Matches Note**
    - **Validates: Requirements 8.2**
  - [ ] 7.3 Write property test for filename derivation rules (Property 21)
    - **Property 21: Filename Derivation Rules**
    - **Validates: Requirements 8.3**
  - [ ] 7.4 Write property test for collision avoidance (Property 22)
    - **Property 22: Collision Avoidance Produces Distinct Filenames**
    - **Validates: Requirements 8.4**
  - [ ] 7.5 Write property test for KB save updates DB record (Property 23)
    - **Property 23: KB Save Updates DB Record**
    - **Validates: Requirements 10.4**

- [ ] 8. Background worker pipeline
  - [ ] 8.1 Implement `workers/pipeline.py` — `async def run_job(job_id: str, session: Session)`
    - Stages: load job → set `running` → scrape → de-noise → synthesize → persist `MarkdownNote` → set `done`
    - Append log entries after each stage; catch all exceptions at the top level, set `failed`, append error message
    - Route to `StaticScraper` or `DynamicScraper` based on `job.engine`
    - _Requirements: 2.2, 2.3, 4.5, 9.1_
  - [ ] 8.2 Write property test for successful synthesis produces done job (Property 10)
    - **Property 10: Successful Synthesis Produces Done Job and Persisted Note**
    - **Validates: Requirements 4.5**
  - [ ] 8.3 Write property test for status transitions reflected in DB (Property 12)
    - **Property 12: Status Transitions Are Immediately Reflected in DB**
    - **Validates: Requirements 5.2**

- [ ] 9. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. API layer — URL ingestion and job endpoints
  - [ ] 10.1 Implement `api/scrape.py` — `POST /v1/scrape`
    - Validate each URL (must be `http`/`https`); return 422 with per-URL detail for invalid URLs
    - Create a `Job` record per URL with `status=queued`; enqueue `run_job` via `BackgroundTasks`; return job list within 500ms
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 9.1_
  - [ ] 10.2 Implement `api/jobs.py` — `GET /v1/jobs/{job_id}`
    - Return job fields: `job_id`, `status`, `logs` (decoded from JSON), `created_at`, `updated_at`; return 404 for unknown IDs
    - _Requirements: 5.1, 5.5_
  - [ ] 10.3 Implement `api/jobs.py` — `POST /v1/jobs/{job_id}/rerun`
    - Load existing job's raw Markdown from its latest note; enqueue a new `synthesize` call with the new `template_id`; create a new `MarkdownNote` record with incremented version
    - Do NOT invoke the scraper
    - _Requirements: 7.1, 7.2, 7.3_
  - [ ] 10.4 Write property test for URL validation correctness (Property 1)
    - **Property 1: URL Validation Correctness**
    - **Validates: Requirements 1.2, 1.3**
  - [ ] 10.5 Write property test for job status response fields (Property 11)
    - **Property 11: Job Status Response Contains Required Fields**
    - **Validates: Requirements 5.1**
  - [ ] 10.6 Write property test for 404 on non-existent job (Property 14)
    - **Property 14: 404 for Non-Existent Job**
    - **Validates: Requirements 5.5**
  - [ ] 10.7 Write property test for re-run does not re-scrape (Property 17)
    - **Property 17: Re-Run Does Not Re-Scrape**
    - **Validates: Requirements 7.2**
  - [ ] 10.8 Write property test for version count invariant (Property 18)
    - **Property 18: Version Count Invariant**
    - **Validates: Requirements 7.3**

- [ ] 11. API layer — Notes endpoints
  - [ ] 11.1 Implement `api/notes.py` — `GET /v1/notes/{job_id}`
    - Return all `MarkdownNote` records for the job ordered by `created_at` descending; return 404 if job not found
    - _Requirements: 7.5, 10.3_
  - [ ] 11.2 Implement `api/notes.py` — `PUT /v1/notes/{note_id}`
    - Update `title` and `content`; return updated note; return 404 for unknown note IDs
    - _Requirements: 6.3, 6.4, 6.5_
  - [ ] 11.3 Implement `api/notes.py` — `POST /v1/notes/{note_id}/save`
    - Call `save_to_kb`; update `MarkdownNote.saved_path` in DB; return the file path
    - _Requirements: 8.1, 8.2, 8.5, 10.4_
  - [ ] 11.4 Wire all routers into `main.py` with `create_db_and_tables()` on startup lifespan
    - _Requirements: 10.2_
  - [ ] 11.5 Write property test for note edit round-trip (Property 15)
    - **Property 15: Note Edit Round-Trip**
    - **Validates: Requirements 6.3, 6.4**
  - [ ] 11.6 Write property test for 404 on non-existent note PUT (Property 16)
    - **Property 16: 404 for Non-Existent Note on PUT**
    - **Validates: Requirements 6.5**
  - [ ] 11.7 Write property test for notes ordered by timestamp descending (Property 19)
    - **Property 19: Notes Ordered by Timestamp Descending**
    - **Validates: Requirements 7.5, 10.3**

- [ ] 12. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Streamlit frontend
  - [ ] 13.1 Implement `ui/app.py` with sidebar radio navigation for Workspace, Library, and Templates pages
    - Import and render each page module based on selection
    - _Requirements: 9.1_
  - [ ] 13.2 Implement `ui/pages/workspace.py` — Workspace page
    - URL text area input, engine toggle (static/dynamic), template dropdown populated from `GET /v1/templates` (or seeded list)
    - On submit: call `POST /v1/scrape`, store returned `job_id` in `st.session_state`
    - Poll `GET /v1/jobs/{job_id}` every 3 seconds using `time.sleep(3)` + `st.rerun()` while job is `queued` or `running`; display status and logs
    - When `done`: show raw Markdown and AI note side-by-side; provide editable text area; on save call `PUT /v1/notes/{note_id}`
    - When `failed`: display error message from logs
    - Provide "Re-run AI" button that calls `POST /v1/jobs/{job_id}/rerun` with a new template selection
    - _Requirements: 1.1, 2.1, 4.1, 5.3, 5.4, 6.1, 6.2, 7.1, 7.4_
  - [ ] 13.3 Implement `ui/pages/library.py` — Library page
    - Fetch all notes via `GET /v1/notes/{job_id}` for all known jobs; display version history with template name and timestamp
    - Provide "Save to Knowledge Base" button per note that calls `POST /v1/notes/{note_id}/save` and displays the returned file path
    - _Requirements: 7.4, 8.1, 8.5_
  - [ ] 13.4 Implement `ui/pages/templates.py` — Templates page
    - List all templates; provide editable fields for `name` and `prompt_template`; persist changes via API
    - _Requirements: 4.1_
  - [ ] 13.5 Write property test for failed job error message rendered in UI (Property 13)
    - **Property 13: Failed Job Error Message Rendered in UI**
    - **Validates: Requirements 5.4**

- [ ] 14. Integration tests
  - [ ] 14.1 Write pipeline smoke test
    - POST a URL with mocked `StaticScraper` and mocked LLM client; assert job reaches `done` and a `MarkdownNote` is in the DB
    - _Requirements: 4.5, 9.1_
  - [ ] 14.2 Write concurrency smoke test
    - Submit 5 simultaneous jobs; assert all `GET /v1/jobs/{job_id}` status-check requests respond within 500ms
    - _Requirements: 9.3_
  - [ ] 14.3 Write DB initialization test
    - Start API with no DB file; assert schema is created and default templates are seeded
    - _Requirements: 10.2_

- [ ] 15. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with `max_examples=100` and a comment referencing the property number
- Unit tests and property tests are complementary — avoid duplicating coverage
