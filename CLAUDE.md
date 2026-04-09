# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WebScribe converts web pages into structured Markdown notes using LLMs. It consists of two separate processes: a FastAPI backend with async workers and a Streamlit frontend.

## Architecture

### Dual-Process Design

The system runs as **two independent processes** that communicate via HTTP:

1. **FastAPI Backend** (`main.py`): REST API + SQLite database + background workers
2. **Streamlit Frontend** (`ui/app.py`): Browser UI that polls the API

Both must be running simultaneously for the full application to work.

### Worker Pipeline Flow

Jobs progress through 5 stages orchestrated by `workers/pipeline.py`:

```
URL Input → Scraper → De-noiser → AI Engine → Database → Knowledge Base (optional)
```

**Critical**: Background tasks run with FastAPI's `BackgroundTasks`, which means:
- Database sessions must be passed to workers (not created inside)
- Session state is NOT shared between the HTTP request and background task
- Use `session.refresh(job)` after commits when checking state immediately

### Component Responsibilities

- **Scrapers** (`scrapers/`): Return raw HTML only. No parsing, no content extraction.
- **De-noiser** (`denoiser/cleaner.py`): HTML → Markdown conversion. Removes `<header>`, `<footer>`, `<nav>`, `<aside>`, `<script>`, `<style>`.
- **AI Engine** (`ai_engine/engine.py`): Takes Markdown, returns structured `MarkdownNote` using Jinja2 templates.
- **KB Writer** (`kb/writer.py`): Filesystem operations only. Derives filenames, handles collisions.

## Development Commands

### Setup

```bash
# Install dependencies
pip install -e .

# Install Playwright browser for dynamic scraping
python -m playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env and add your LLM_API_KEY
```

### Running

```bash
# Start backend (terminal 1)
python main.py

# Start frontend (terminal 2)
streamlit run ui/app.py

# Or use the startup script (Windows)
start.bat
```

### Testing

```bash
# Run all tests
python -m pytest

# Run specific test suite
python -m pytest tests/unit/
python -m pytest tests/api/
python -m pytest tests/integration/

# Run single test file
python -m pytest tests/unit/test_denoiser.py -v

# Run single test function
python -m pytest tests/unit/test_denoiser.py::test_markdown_heading_preservation -v

# Show property-based test statistics
python -m pytest tests/unit/test_denoiser.py -v --hypothesis-show-statistics
```

### Database

```bash
# View database
sqlite3 webscribe.db

# Reset database (delete and restart API to recreate)
rm webscribe.db
python main.py
```

## Testing Strategy

This project uses **property-based testing** with Hypothesis alongside traditional unit tests.

### When to Use Each

- **Property tests**: Verify invariants across many inputs (e.g., "all valid URLs pass validation")
- **Unit tests**: Verify specific examples (e.g., "this exact HTML produces this exact Markdown")

### Property Test Structure

All property tests follow this pattern:

```python
# Feature: webscribe, Property N: Description
# Validates: Requirements X.Y, X.Z
@given(param=st.strategy())
@settings(max_examples=100)
def test_property_name(param):
    """Property: Universal statement about behavior"""
    # Test implementation
```

### Important Testing Notes

- Property tests are in `tests/unit/` alongside unit tests
- Integration tests are in `tests/integration/`
- API endpoint tests are in `tests/api/`
- Each property test validates specific requirements from `.kiro/specs/webscribe/requirements.md`
- Use `assume()` in property tests to filter out invalid inputs, not `if` statements

## Key Architectural Constraints

### Database Session Management

**Problem**: SQLModel sessions don't work across async boundaries in FastAPI background tasks.

**Solution**: 
- Pass the session to `run_job()` as a parameter
- The session is created in the HTTP handler scope
- Background task inherits this session

**Wrong**:
```python
async def run_job(job_id: str):
    with get_session() as session:  # New session, won't see committed data
        job = session.get(Job, job_id)
```

**Correct**:
```python
async def run_job(job_id: str, session: Session):
    job = session.get(Job, job_id)  # Uses passed session
```

### Jinja2 Template Variables

AI templates in `database.py` must use `{{ raw_markdown }}` as the variable name. This is the contract between the worker pipeline and AI engine.

The de-noiser outputs `raw_markdown` → worker passes it to AI engine → AI engine injects it into the template.

### Scraper Engine Selection

The `engine` field in Job determines which scraper runs:
- `"static"` → `StaticScraper` (httpx)
- `"dynamic"` → `DynamicScraper` (Playwright)

This routing happens in `workers/pipeline.py:_scrape_url()`.

### Filename Derivation Rules

KB writer derives filenames using strict rules (see `kb/writer.py:_derive_filename_slug()`):
1. Lowercase
2. Replace `[^a-z0-9]+` with `-`
3. Collapse `--+` to `-`
4. Strip leading/trailing `-`
5. Default to `"untitled"` if empty

**This is property-tested**, so changes must maintain these invariants.

## Configuration

All config is environment-based via `.env` (loaded by `python-dotenv`):

- **Required**: `LLM_API_KEY` - Without this, jobs will fail at AI synthesis stage
- **Optional**: Everything else has sensible defaults

Config is loaded once at import time in `config.py`. To change config, modify `.env` and restart both processes.

## Common Development Patterns

### Adding a New Scraper

1. Subclass `BaseScraper` in `scrapers/`
2. Implement `async def fetch(self, url: str) -> ScraperResult`
3. Add routing logic to `workers/pipeline.py:_scrape_url()`
4. Add property test to `tests/unit/test_scraper_routing.py`

### Adding a New API Endpoint

1. Create route function in appropriate router (`api/scrape.py`, `api/jobs.py`, `api/notes.py`)
2. Use `Depends(get_session_dependency)` for database access
3. Add Pydantic request/response models
4. Update `main.py` if creating a new router (use `app.include_router()`)

### Adding a New AI Template

Templates are seeded in `database.py:create_db_and_tables()`. To add a new one:

1. Add a new `Template(id="...", name="...", prompt_template="...")` to the seed list
2. Ensure template uses `{{ raw_markdown }}` variable
3. Delete `webscribe.db` and restart to re-seed

## Troubleshooting

### "Module not found" in Streamlit

Streamlit runs from a different working directory. The UI imports add project root to `sys.path` in `ui/app.py`. If modules still aren't found, check that `sys.path.insert(0, str(project_root))` runs before other imports.

### Jobs Stuck in "running" State

1. Check FastAPI terminal for exceptions
2. Verify `LLM_API_KEY` is set in `.env`
3. Check that the worker didn't crash (errors should update job status to "failed")
4. If worker is still running but job appears stuck, check database sessions aren't being created inside the worker

### Tests Fail with "Can't access file" on Windows

SQLite may hold file locks. Use `engine.dispose()` in test teardown:

```python
finally:
    test_engine.dispose()
    tmp_db_path.unlink()
```

### Dynamic Scraper Times Out

Default timeout is 30 seconds. For slow sites:
1. Set `DYNAMIC_SCRAPER_TIMEOUT=60` in `.env`
2. Or use `static` engine if JavaScript isn't needed
