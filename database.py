"""
WebScribe Database Initialization

Handles SQLite database setup, schema creation, and session management.
"""

from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine, select

from config import DATABASE_URL
from models import Template


# Create database engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query debugging
    connect_args={"check_same_thread": False}  # Needed for SQLite
)


def create_db_and_tables():
    """
    Initialize the database schema and seed default templates.

    Creates all tables defined in SQLModel classes and inserts
    default Template records if the template table is empty.
    """
    # Create all tables
    SQLModel.metadata.create_all(engine)

    # Seed default templates if table is empty
    with Session(engine) as session:
        existing_templates = session.exec(select(Template)).first()

        if not existing_templates:
            default_templates = [
                Template(
                    id="research-summary",
                    name="Research Summary",
                    prompt_template="""You are a research assistant. Convert the following web content into a structured research note.

# Web Content:
{{ raw_markdown }}

# Instructions:
Generate a well-structured Markdown note with:
1. A concise title (extract from content)
2. Executive Summary (2-3 sentences)
3. Key Concepts (bullet list of main ideas)
4. Extracted code snippets (if any, with proper syntax highlighting)
5. Action items or next steps (if applicable)
6. Relevant tags for categorization

Return ONLY the formatted Markdown note, no additional commentary."""
                ),
                Template(
                    id="beginner-explainer",
                    name="Beginner Explainer",
                    prompt_template="""You are a teacher explaining technical content to beginners. Convert the following web content into an easy-to-understand note.

# Web Content:
{{ raw_markdown }}

# Instructions:
Generate a beginner-friendly Markdown note with:
1. A clear, descriptive title
2. Simple Summary (explain in plain language)
3. Key Terms Explained (define technical terms)
4. Step-by-Step Guide (if the content describes a process)
5. Common Pitfalls (if applicable)
6. Further Reading suggestions
7. Tags for organization

Use analogies and simple language. Return ONLY the formatted Markdown note."""
                ),
                Template(
                    id="api-endpoint-extractor",
                    name="API Endpoint Extractor",
                    prompt_template="""You are an API documentation specialist. Extract API endpoint information from the following web content.

# Web Content:
{{ raw_markdown }}

# Instructions:
Generate a structured API reference note with:
1. Title (API name or service)
2. Overview (purpose of the API)
3. Endpoints Table (method, path, description)
4. Authentication (if mentioned)
5. Request/Response Examples (extract code blocks)
6. Rate Limits and Notes
7. Tags (e.g., REST, GraphQL, authentication type)

Return ONLY the formatted Markdown note with extracted API information."""
                )
            ]

            for template in default_templates:
                session.add(template)

            session.commit()
            print(f"✓ Seeded {len(default_templates)} default templates")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Provides a SQLModel session for database operations.
    Ensures the session is properly closed after use.

    Yields:
        Session: A SQLModel database session
    """
    with Session(engine) as session:
        yield session


def get_session_dependency():
    """
    FastAPI dependency function for injecting database sessions.

    Use with FastAPI's Depends() to get a session in route handlers:
        session: Session = Depends(get_session_dependency)
    """
    with get_session() as session:
        yield session
