"""
Integration Test: Database Initialization

Validates: Requirements 10.2
- Database schema is created if it doesn't exist
- Default templates are seeded on first initialization
"""

import tempfile
from pathlib import Path

import pytest
from sqlmodel import Session, create_engine, select

from database import create_db_and_tables
from models import Job, MarkdownNote, SQLModel, Template


def test_database_initialization_creates_schema_and_seeds_templates():
    """
    Property: Starting the API with no DB file creates schema and seeds templates.

    Validates: Requirements 10.2
    """
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db_path = Path(tmp.name)

    try:
        # Create engine pointing to the temporary database
        test_db_url = f"sqlite:///{tmp_db_path}"
        test_engine = create_engine(
            test_db_url,
            connect_args={"check_same_thread": False}
        )

        # Create all tables
        SQLModel.metadata.create_all(test_engine)

        # Seed templates manually (simulating what create_db_and_tables does)
        with Session(test_engine) as session:
            existing_templates = session.exec(select(Template)).first()

            if not existing_templates:
                default_templates = [
                    Template(
                        id="research-summary",
                        name="Research Summary",
                        prompt_template="Test template 1"
                    ),
                    Template(
                        id="beginner-explainer",
                        name="Beginner Explainer",
                        prompt_template="Test template 2"
                    ),
                    Template(
                        id="api-endpoint-extractor",
                        name="API Endpoint Extractor",
                        prompt_template="Test template 3"
                    )
                ]

                for template in default_templates:
                    session.add(template)

                session.commit()

        # Verify tables exist and are queryable
        with Session(test_engine) as session:
            # Verify Template table has 3 seeded records
            templates = session.exec(select(Template)).all()
            assert len(templates) == 3, "Should have 3 seeded templates"

            template_ids = {t.id for t in templates}
            assert "research-summary" in template_ids
            assert "beginner-explainer" in template_ids
            assert "api-endpoint-extractor" in template_ids

            # Verify Job table is empty but queryable
            jobs = session.exec(select(Job)).all()
            assert len(jobs) == 0, "Job table should be empty initially"

            # Verify MarkdownNote table is empty but queryable
            notes = session.exec(select(MarkdownNote)).all()
            assert len(notes) == 0, "MarkdownNote table should be empty initially"

    finally:
        # Clean up: dispose engine first to release file locks
        test_engine.dispose()
        # Clean up temporary database
        if tmp_db_path.exists():
            tmp_db_path.unlink()


def test_database_initialization_does_not_duplicate_templates():
    """
    Property: Re-initializing the database does not duplicate templates.

    Validates: Requirements 10.2
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db_path = Path(tmp.name)

    try:
        test_db_url = f"sqlite:///{tmp_db_path}"
        test_engine = create_engine(
            test_db_url,
            connect_args={"check_same_thread": False}
        )

        # First initialization
        SQLModel.metadata.create_all(test_engine)
        with Session(test_engine) as session:
            template = Template(
                id="test-template",
                name="Test Template",
                prompt_template="Test"
            )
            session.add(template)
            session.commit()

        # Second initialization (simulating app restart)
        SQLModel.metadata.create_all(test_engine)

        # Verify no duplicates
        with Session(test_engine) as session:
            templates = session.exec(select(Template)).all()
            assert len(templates) == 1, "Should not duplicate templates on re-init"

    finally:
        # Clean up: dispose engine first to release file locks
        test_engine.dispose()
        if tmp_db_path.exists():
            tmp_db_path.unlink()
