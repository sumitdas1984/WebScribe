"""
Unit Tests: Knowledge Base File Writer

Property 20: KB File Content Matches Note
Validates: Requirements 8.2

Property 21: Filename Derivation Rules
Validates: Requirements 8.3

Property 22: Collision Avoidance Produces Distinct Filenames
Validates: Requirements 8.4

Property 23: KB Save Updates DB Record
Validates: Requirements 10.4 (will be tested in integration tests)
"""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from kb.writer import save_to_kb, _derive_filename_slug, _get_available_filename
from models import MarkdownNote


# Feature: webscribe, Property 20: KB file content matches note
@given(content=st.text(min_size=50, max_size=500))
@settings(max_examples=100)
def test_kb_file_content_matches_note(content):
    """
    Property: Saved file content is byte-for-byte equal to note's content field.

    Validates: Requirements 8.2
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_dir = Path(tmpdir)

        note = MarkdownNote(
            job_id="test-job",
            title="Test Note",
            content=content,
            template_id="test-template"
        )

        # Save to KB
        saved_path = save_to_kb(note, kb_dir)

        # Verify file exists
        assert saved_path.exists(), "File should be created"

        # Verify content matches exactly (read with newline='' to preserve line endings)
        with open(saved_path, "r", encoding="utf-8", newline="") as f:
            saved_content = f.read()
        assert saved_content == content, "File content should match note content exactly"


# Feature: webscribe, Property 21: Filename derivation rules
@given(
    title=st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=1,
        max_size=100
    )
)
@settings(max_examples=100)
def test_filename_derivation_rules(title):
    """
    Property: Derived filename is lowercase, contains only [a-z0-9-], doesn't start/end with hyphen, ends with .md.

    Validates: Requirements 8.3
    """
    assume(title.strip())  # Ensure non-empty after stripping

    slug = _derive_filename_slug(title)

    # Check lowercase
    assert slug == slug.lower(), "Slug should be lowercase"

    # Check character set (only a-z, 0-9, and hyphens)
    assert all(c.isalnum() or c == "-" for c in slug), \
        "Slug should contain only alphanumeric characters and hyphens"

    # Check doesn't start or end with hyphen
    if slug:  # Non-empty slugs
        assert not slug.startswith("-"), "Slug should not start with hyphen"
        assert not slug.endswith("-"), "Slug should not end with hyphen"


def test_filename_derivation_specific_examples():
    """
    Test specific examples of filename derivation.

    Validates: Requirements 8.3
    """
    test_cases = [
        ("FastAPI: A Deep Dive!", "fastapi-a-deep-dive"),
        ("Python & Django", "python-django"),
        ("Hello   World", "hello-world"),
        ("   Trimmed   ", "trimmed"),
        ("Multiple---Hyphens", "multiple-hyphens"),
        ("CamelCaseTitle", "camelcasetitle"),
        ("Title with (parentheses)", "title-with-parentheses"),
        ("Email@example.com", "email-example-com"),
        ("123 Numbers", "123-numbers"),
    ]

    for title, expected_slug in test_cases:
        slug = _derive_filename_slug(title)
        assert slug == expected_slug, f"Expected '{expected_slug}' for title '{title}', got '{slug}'"


def test_filename_derivation_empty_title():
    """
    Verify that empty or whitespace-only titles get a default slug.

    Validates: Requirements 8.3
    """
    assert _derive_filename_slug("") == "untitled"
    assert _derive_filename_slug("   ") == "untitled"
    assert _derive_filename_slug("!!!") == "untitled"


# Feature: webscribe, Property 22: Collision avoidance produces distinct filenames
def test_collision_avoidance_produces_distinct_filenames():
    """
    Property: Saving N notes with the same title produces N distinct files.

    Validates: Requirements 8.4
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_dir = Path(tmpdir)

        title = "My Note"
        num_notes = 5

        saved_paths = []

        for i in range(num_notes):
            note = MarkdownNote(
                job_id=f"job-{i}",
                title=title,
                content=f"Content for note {i}",
                template_id="test-template"
            )

            path = save_to_kb(note, kb_dir)
            saved_paths.append(path)

        # Verify all paths are distinct
        assert len(set(saved_paths)) == num_notes, "All paths should be unique"

        # Verify all files exist
        for path in saved_paths:
            assert path.exists(), f"File {path} should exist"

        # Verify filenames follow the pattern
        filenames = [p.name for p in saved_paths]
        assert "my-note.md" in filenames, "First file should be my-note.md"
        assert "my-note-2.md" in filenames, "Second file should be my-note-2.md"
        assert "my-note-3.md" in filenames, "Third file should be my-note-3.md"
        assert "my-note-4.md" in filenames, "Fourth file should be my-note-4.md"
        assert "my-note-5.md" in filenames, "Fifth file should be my-note-5.md"


def test_get_available_filename_no_collision():
    """
    Verify _get_available_filename returns base slug when no collision exists.

    Validates: Requirements 8.4
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_dir = Path(tmpdir)

        filename = _get_available_filename(kb_dir, "test-note")
        assert filename == "test-note.md", "Should return base filename when no collision"


def test_get_available_filename_with_collision():
    """
    Verify _get_available_filename appends suffix when collision exists.

    Validates: Requirements 8.4
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_dir = Path(tmpdir)

        # Create first file
        (kb_dir / "test-note.md").write_text("content 1")

        # Get next available filename
        filename = _get_available_filename(kb_dir, "test-note")
        assert filename == "test-note-2.md", "Should append -2 for first collision"

        # Create second file
        (kb_dir / "test-note-2.md").write_text("content 2")

        # Get next available filename
        filename = _get_available_filename(kb_dir, "test-note")
        assert filename == "test-note-3.md", "Should append -3 for second collision"


def test_save_to_kb_creates_directory_if_not_exists():
    """
    Verify save_to_kb creates the KB directory if it doesn't exist.

    Validates: Requirements 8.2
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # KB dir inside tmpdir that doesn't exist yet
        kb_dir = Path(tmpdir) / "nonexistent" / "kb"

        assert not kb_dir.exists(), "KB dir should not exist before save"

        note = MarkdownNote(
            job_id="test-job",
            title="Test Note",
            content="Test content for directory creation test.",
            template_id="test-template"
        )

        saved_path = save_to_kb(note, kb_dir)

        assert kb_dir.exists(), "KB dir should be created"
        assert saved_path.exists(), "File should be saved"


def test_save_to_kb_returns_absolute_path():
    """
    Verify save_to_kb returns an absolute path.

    Validates: Requirements 8.2
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_dir = Path(tmpdir)

        note = MarkdownNote(
            job_id="test-job",
            title="Test Note",
            content="Test content.",
            template_id="test-template"
        )

        saved_path = save_to_kb(note, kb_dir)

        assert saved_path.is_absolute(), "Returned path should be absolute"
