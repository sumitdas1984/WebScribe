"""
WebScribe Configuration

Loads application settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{PROJECT_ROOT / 'webscribe.db'}"
)

# Knowledge Base directory - where approved markdown files are saved
KB_DIR = Path(os.getenv(
    "KB_DIR",
    str(PROJECT_ROOT / "knowledge_base")
))

# LLM API configuration
LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://api.openai.com/v1"
)

LLM_API_KEY = os.getenv("LLM_API_KEY", "")

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Scraper configuration
STATIC_SCRAPER_TIMEOUT = int(os.getenv("STATIC_SCRAPER_TIMEOUT", "30"))
DYNAMIC_SCRAPER_TIMEOUT = int(os.getenv("DYNAMIC_SCRAPER_TIMEOUT", "30"))

# Worker configuration
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))

# AI Engine configuration
AI_RETRY_COUNT = int(os.getenv("AI_RETRY_COUNT", "3"))
AI_RETRY_BASE_DELAY = float(os.getenv("AI_RETRY_BASE_DELAY", "1.0"))

# De-noiser configuration
MIN_CONTENT_LENGTH = int(os.getenv("MIN_CONTENT_LENGTH", "50"))

# Ensure KB directory exists
KB_DIR.mkdir(parents=True, exist_ok=True)
