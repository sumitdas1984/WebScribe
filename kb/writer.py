"""
Knowledge Base File Writer

Saves MarkdownNote content to the file system in a structured manner.
"""

import re
from pathlib import Path

from models import MarkdownNote
from config import KB_DIR


def save_to_kb(note: MarkdownNote, kb_dir: Path = KB_DIR) -> Path:
    """
    Save a MarkdownNote to the Knowledge Base directory as a .md file.

    Derives the filename from the note's title following these rules:
    1. Convert to lowercase
    2. Replace non-alphanumeric characters with hyphens
    3. Collapse consecutive hyphens to single hyphen
    4. Strip leading/trailing hyphens
    5. Append .md extension

    If a file with the derived name already exists, appends a numeric
    suffix (-2, -3, etc.) to avoid overwriting.

    Args:
        note: The MarkdownNote to save
        kb_dir: The Knowledge Base directory path (defaults to config KB_DIR)

    Returns:
        Path: The absolute path to the saved file

    Example:
        >>> note = MarkdownNote(title="FastAPI: A Deep Dive!", content="...")
        >>> path = save_to_kb(note)
        >>> print(path.name)
        "fastapi-a-deep-dive.md"
    """
    # Ensure KB directory exists
    kb_dir.mkdir(parents=True, exist_ok=True)

    # Derive filename from title
    slug = _derive_filename_slug(note.title)

    # Handle collision avoidance
    filename = _get_available_filename(kb_dir, slug)

    # Full path to the output file
    output_path = kb_dir / filename

    # Write atomically: write to temp file, then rename
    temp_path = output_path.with_suffix(".tmp")

    try:
        # Write content to temp file (newline='' preserves exact line endings)
        with open(temp_path, "w", encoding="utf-8", newline="") as f:
            f.write(note.content)

        # Atomic rename
        temp_path.rename(output_path)

    except Exception as e:
        # Clean up temp file if something went wrong
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Failed to save note to {output_path}: {str(e)}")

    return output_path


def _derive_filename_slug(title: str) -> str:
    """
    Derive a filesystem-safe slug from a note title.

    Rules:
    1. Convert to lowercase
    2. Replace any non-alphanumeric character with a hyphen
    3. Collapse consecutive hyphens to a single hyphen
    4. Strip leading and trailing hyphens

    Args:
        title: The note title

    Returns:
        A filesystem-safe slug

    Example:
        >>> _derive_filename_slug("FastAPI: A Deep Dive!")
        "fastapi-a-deep-dive"
    """
    # Convert to lowercase
    slug = title.lower()

    # Replace non-alphanumeric characters with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # Collapse consecutive hyphens
    slug = re.sub(r"-+", "-", slug)

    # Strip leading/trailing hyphens
    slug = slug.strip("-")

    # If slug is empty after processing, use a default
    if not slug:
        slug = "untitled"

    return slug


def _get_available_filename(kb_dir: Path, base_slug: str) -> str:
    """
    Get an available filename, appending numeric suffix if needed.

    If base_slug.md doesn't exist, returns it as-is.
    Otherwise, tries base_slug-2.md, base_slug-3.md, etc. until
    an available filename is found.

    Args:
        kb_dir: The Knowledge Base directory
        base_slug: The base filename slug (without .md extension)

    Returns:
        An available filename with .md extension

    Example:
        >>> _get_available_filename(Path("/kb"), "my-note")
        "my-note.md"  # if my-note.md doesn't exist

        >>> _get_available_filename(Path("/kb"), "my-note")
        "my-note-2.md"  # if my-note.md already exists
    """
    # Try the base filename first
    filename = f"{base_slug}.md"
    if not (kb_dir / filename).exists():
        return filename

    # Try with numeric suffixes
    counter = 2
    while True:
        filename = f"{base_slug}-{counter}.md"
        if not (kb_dir / filename).exists():
            return filename
        counter += 1

        # Safety valve to prevent infinite loops
        if counter > 10000:
            raise RuntimeError(f"Could not find available filename for slug: {base_slug}")
