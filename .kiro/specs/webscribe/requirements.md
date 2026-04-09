# Requirements Document

## Introduction

WebScribe is a web-based utility that converts messy web pages into clean, structured Markdown files. It addresses "information hoarding" by scraping web content, de-noising it, and using an LLM to generate structured summaries compatible with knowledge-base tools like Obsidian, Notion, and GitHub wikis. The system consists of a Streamlit frontend, a FastAPI backend, background workers for scraping and AI refinement, and a local SQLite + file-system storage layer.

## Glossary

- **System**: The WebScribe application as a whole.
- **API**: The FastAPI backend service that orchestrates all operations.
- **Scraper**: The component responsible for fetching and extracting content from a URL.
- **Static_Scraper**: The BeautifulSoup-based scraper for static HTML pages.
- **Dynamic_Scraper**: The Playwright-based scraper for JavaScript-rendered pages.
- **De_Noiser**: The logic layer that strips non-content elements (headers, footers, sidebars, ads) from raw HTML.
- **AI_Engine**: The LLM integration component that synthesizes raw Markdown into structured summaries.
- **Worker**: A background task unit that processes a job asynchronously.
- **Job**: A unit of work tracked in the database, representing the full lifecycle of processing one URL.
- **SourceLink**: The data entity representing the original URL and its metadata.
- **MarkdownNote**: The data entity representing the final structured Markdown output for a URL.
- **Knowledge_Base**: The local directory where approved `.md` files are stored.
- **Template**: A named prompt configuration used by the AI_Engine to shape its output (e.g., "Research Summary", "Beginner Explainer", "API Endpoint Extractor").
- **UI**: The Streamlit-based frontend interface.

---

## Requirements

### Requirement 1: URL Ingestion

**User Story:** As a researcher, I want to submit one or more URLs through the UI, so that WebScribe can process them without requiring me to manually copy and paste content.

#### Acceptance Criteria

1. THE UI SHALL provide an input field that accepts a single URL or a newline-separated list of URLs.
2. WHEN a user submits one or more URLs, THE API SHALL validate that each URL is a well-formed HTTP or HTTPS URL.
3. IF a submitted URL is malformed or uses an unsupported scheme, THEN THE API SHALL return a 422 error with a descriptive message identifying the invalid URL.
4. WHEN valid URLs are submitted, THE API SHALL create a Job record for each URL with an initial status of `queued` and return each `job_id` immediately.
5. THE API SHALL respond to a `POST /v1/scrape` request within 500ms regardless of how long the scraping process takes.

---

### Requirement 2: Scraper Engine Selection

**User Story:** As a user, I want to choose between a fast static scraper and a dynamic scraper, so that I can handle both simple blogs and JavaScript-heavy sites effectively.

#### Acceptance Criteria

1. THE UI SHALL provide a toggle to select either the Static_Scraper or the Dynamic_Scraper before submitting a URL.
2. WHEN a Job is dispatched with the `static` engine option, THE Worker SHALL use the Static_Scraper to fetch and parse the page.
3. WHEN a Job is dispatched with the `dynamic` engine option, THE Worker SHALL use the Dynamic_Scraper to fetch and parse the page.
4. THE Static_Scraper SHALL use BeautifulSoup to parse the raw HTML response.
5. THE Dynamic_Scraper SHALL use Playwright to render the page and retrieve the fully hydrated DOM before parsing.
6. IF the Dynamic_Scraper fails to render a page within 30 seconds, THEN THE Worker SHALL mark the Job status as `failed` and record the timeout error in the Job logs.

---

### Requirement 3: Content De-Noising

**User Story:** As a user, I want the scraper to strip away navigation, ads, and other non-content elements, so that only the meaningful article content is passed to the AI.

#### Acceptance Criteria

1. WHEN raw HTML is retrieved, THE De_Noiser SHALL attempt to extract content from the `<main>` or `<article>` HTML element first.
2. IF neither a `<main>` nor an `<article>` element is present, THEN THE De_Noiser SHALL fall back to extracting the `<body>` content.
3. THE De_Noiser SHALL remove all `<header>`, `<footer>`, `<nav>`, `<aside>`, and `<script>` elements from the extracted content before conversion.
4. THE De_Noiser SHALL convert the cleaned HTML into Markdown, preserving headings, lists, code blocks, and hyperlinks.
5. IF the resulting Markdown content is fewer than 50 characters after de-noising, THEN THE Worker SHALL mark the Job status as `failed` and log a "no extractable content" error.

---

### Requirement 4: AI Synthesis

**User Story:** As a researcher, I want the system to use an LLM to generate a structured summary of the scraped content, so that I get a ready-to-use knowledge note without manual effort.

#### Acceptance Criteria

1. THE UI SHALL present a dropdown of available Templates before job submission.
2. WHEN a Job reaches the refinement stage, THE AI_Engine SHALL send the raw Markdown content and the selected Template prompt to the configured LLM.
3. THE AI_Engine SHALL produce a MarkdownNote containing: a title, an executive summary, a list of key concepts, extracted code snippets (if any), action items (if any), and a list of tags.
4. IF the LLM API call fails or returns an error, THEN THE AI_Engine SHALL retry the request up to 3 times with exponential backoff before marking the Job as `failed`.
5. WHEN the AI_Engine completes successfully, THE Worker SHALL update the Job status to `done` and persist the MarkdownNote to the database.

---

### Requirement 5: Job Status Tracking

**User Story:** As a user, I want to monitor the progress of my submitted URLs in real time, so that I know when processing is complete without refreshing the page.

#### Acceptance Criteria

1. THE API SHALL expose a `GET /v1/jobs/{job_id}` endpoint that returns the current Job status, progress logs, and timestamps.
2. WHEN a Job transitions between statuses (`queued` → `running` → `done` or `failed`), THE API SHALL update the Job record in the database immediately.
3. THE UI SHALL poll `GET /v1/jobs/{job_id}` at a maximum interval of 3 seconds and display the current status to the user.
4. WHEN a Job status is `failed`, THE UI SHALL display the error message from the Job logs to the user.
5. THE API SHALL return a 404 response when `GET /v1/jobs/{job_id}` is called with a non-existent `job_id`.

---

### Requirement 6: Review and Edit

**User Story:** As a researcher, I want to view the raw scraped Markdown and the AI summary side by side and edit them before saving, so that I can correct any errors before committing to my knowledge base.

#### Acceptance Criteria

1. WHEN a Job status is `done`, THE UI SHALL display the raw scraped Markdown and the AI-generated MarkdownNote in a side-by-side view.
2. THE UI SHALL provide an editable text area for the MarkdownNote content.
3. WHEN a user submits edits, THE API SHALL accept a `PUT /v1/notes/{id}` request and persist the updated content to the database.
4. THE API SHALL return the updated MarkdownNote in the response to a successful `PUT /v1/notes/{id}` request.
5. IF a `PUT /v1/notes/{id}` request references a non-existent note ID, THEN THE API SHALL return a 404 response.

---

### Requirement 7: Versioned Summaries

**User Story:** As a researcher, I want to re-run the AI synthesis with a different template on the same scraped content, so that I can generate multiple perspectives without re-scraping the page.

#### Acceptance Criteria

1. THE UI SHALL provide a "Re-run AI" action on any completed Job that allows the user to select a different Template.
2. WHEN a "Re-run AI" action is triggered, THE AI_Engine SHALL generate a new MarkdownNote using the existing raw Markdown and the newly selected Template, without re-fetching the URL.
3. THE System SHALL store each MarkdownNote version as a separate record linked to the same Job, preserving all prior versions.
4. THE UI SHALL display a version history list for each Job, showing the Template name and creation timestamp for each version.
5. THE API SHALL expose a `GET /v1/notes/{job_id}` endpoint that returns all MarkdownNote versions associated with a Job, ordered by creation timestamp descending.

---

### Requirement 8: Save to Knowledge Base

**User Story:** As a researcher, I want to approve and save a note to my local knowledge base with one click, so that my structured Markdown files are organized and ready for use in Obsidian or similar tools.

#### Acceptance Criteria

1. THE UI SHALL provide a "Save to Knowledge Base" action for any MarkdownNote version.
2. WHEN a "Save to Knowledge Base" action is triggered, THE System SHALL write the MarkdownNote content to a `.md` file in the configured Knowledge_Base directory.
3. THE System SHALL derive the filename from the MarkdownNote title, replacing spaces and special characters with hyphens and converting to lowercase.
4. IF a file with the same derived filename already exists in the Knowledge_Base directory, THEN THE System SHALL append a numeric suffix (e.g., `-2`, `-3`) to the filename to avoid overwriting.
5. WHEN a file is successfully written, THE UI SHALL display the full file path to the user.

---

### Requirement 9: Asynchronous Processing

**User Story:** As a user, I want the UI to remain responsive while URLs are being processed, so that I can submit additional URLs or review completed results without waiting.

#### Acceptance Criteria

1. THE API SHALL process all scraping and AI refinement tasks as background Workers, decoupled from the HTTP request/response cycle.
2. WHILE a Worker is running, THE API SHALL remain available to accept new `POST /v1/scrape` requests.
3. THE System SHALL support processing at least 5 concurrent Jobs without degrading API response times beyond 500ms for status-check requests.

---

### Requirement 10: Data Persistence

**User Story:** As a user, I want my jobs and notes to persist between sessions, so that I can return to previously processed content without re-running the pipeline.

#### Acceptance Criteria

1. THE System SHALL use a SQLite database to persist all Job and MarkdownNote records.
2. WHEN the API starts, THE System SHALL initialize the SQLite database schema if it does not already exist.
3. THE API SHALL expose a `GET /v1/notes/{job_id}` endpoint that retrieves all MarkdownNote records associated with a given Job from the database.
4. WHEN a MarkdownNote is saved to the Knowledge_Base, THE System SHALL update the MarkdownNote record in the database with the saved file path.
