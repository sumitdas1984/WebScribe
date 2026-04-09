# WebScribe

A web-based utility that converts messy web pages into clean, structured Markdown files. WebScribe scrapes web content, removes noise, and uses an LLM to generate structured summaries compatible with knowledge-base tools like Obsidian, Notion, and GitHub wikis.

## Features

- 🌐 **Dual Scraping Modes**: Static (fast) and Dynamic (JavaScript-enabled) scrapers
- 🧹 **Smart De-noising**: Automatically removes headers, footers, ads, and navigation
- 🤖 **AI-Powered Synthesis**: Generates structured notes with summaries, key concepts, and tags
- 📝 **Multiple Templates**: Research summaries, beginner explanations, API documentation
- 💾 **Knowledge Base Integration**: Save notes directly to your local knowledge base
- 🔄 **Version Control**: Re-run AI synthesis with different templates
- 🎨 **User-Friendly UI**: Streamlit interface for easy interaction

## Architecture

```
┌─────────────────┐
│  Streamlit UI   │
└────────┬────────┘
         │ HTTP
┌────────▼────────┐
│   FastAPI       │
│   Backend       │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Workers │
    └────┬────┘
         │
  ┌──────┼──────┬──────┬──────┐
  │      │      │      │      │
┌─▼──┐ ┌─▼──┐ ┌─▼──┐ ┌─▼──┐ ┌─▼──┐
│Scra││De- ││AI  ││KB  ││DB  │
│per ││nois││Eng.││Writ││    │
└────┘ └────┘ └────┘ └────┘ └────┘
```

## Quick Start

### Prerequisites

- Python 3.13+
- OpenAI API key (or compatible LLM API)

### Installation

```bash
# Clone the repository
cd webscribe

# Install dependencies
uv pip install -e .

# Install Playwright browser (for dynamic scraping)
python -m playwright install chromium
```

### Configuration

Set environment variables:

```bash
# Required: Your LLM API key
export LLM_API_KEY="your-api-key-here"

# Optional: Custom configuration
export LLM_BASE_URL="https://api.openai.com/v1"  # Default
export LLM_MODEL="gpt-4o-mini"  # Default
export KB_DIR="./knowledge_base"  # Default
```

### Running the Application

**1. Start the FastAPI backend:**

```bash
python main.py
```

The API will be available at `http://localhost:8000`

**2. Start the Streamlit UI (in a new terminal):**

```bash
streamlit run ui/app.py
```

The UI will open in your browser at `http://localhost:8501`

## Usage

### Using the UI

1. **Workspace**: Submit URLs, monitor progress, edit generated notes
2. **Library**: Browse saved notes, export to Knowledge Base
3. **Templates**: View and manage AI prompt templates

### Using the API

```bash
# Submit a URL for scraping
curl -X POST http://localhost:8000/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com"],
    "engine": "static",
    "template_id": "research-summary"
  }'

# Get job status
curl http://localhost:8000/v1/jobs/{job_id}

# Get generated notes
curl http://localhost:8000/v1/notes/{job_id}

# Save note to Knowledge Base
curl -X POST http://localhost:8000/v1/notes/{note_id}/save
```

## Testing

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=html

# Run specific test suite
python -m pytest tests/unit/
python -m pytest tests/api/
python -m pytest tests/integration/
```

## Project Structure

```
webscribe/
├── api/              # FastAPI endpoints
├── workers/          # Background job pipeline
├── scrapers/         # Static and dynamic scrapers
├── denoiser/         # HTML cleaning and Markdown conversion
├── ai_engine/        # LLM integration
├── kb/               # Knowledge Base file writer
├── ui/               # Streamlit frontend
├── tests/            # Test suite
├── config.py         # Configuration
├── models.py         # SQLModel data models
├── database.py       # Database initialization
└── main.py           # FastAPI app entry point
```

## Configuration

All configuration is done via environment variables. See `config.py` for available options:

- `DATABASE_URL`: SQLite database path
- `KB_DIR`: Knowledge Base directory
- `LLM_BASE_URL`: LLM API base URL
- `LLM_API_KEY`: LLM API key
- `LLM_MODEL`: Model to use
- `STATIC_SCRAPER_TIMEOUT`: Timeout for static scraper (seconds)
- `DYNAMIC_SCRAPER_TIMEOUT`: Timeout for dynamic scraper (seconds)

## Development

### Running Tests

```bash
# All tests
python -m pytest -v

# Unit tests only
python -m pytest tests/unit/ -v

# API tests only
python -m pytest tests/api/ -v

# With property-based testing verbose output
python -m pytest tests/unit/test_denoiser.py -v --hypothesis-show-statistics
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or PR.

## Support

For issues or questions, please open a GitHub issue.
