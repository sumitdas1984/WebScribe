"""
AI Synthesis Engine

Integrates with LLM APIs to generate structured Markdown notes from raw content.
"""

import asyncio
import json
from typing import Dict, Any

from jinja2 import Template as Jinja2Template
from openai import AsyncOpenAI

from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, AI_RETRY_COUNT, AI_RETRY_BASE_DELAY
from models import Template, MarkdownNote
from ai_engine.exceptions import AIEngineError


# Initialize OpenAI client
client = AsyncOpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY
)


async def synthesize(
    raw_markdown: str,
    template: Template,
    job_id: str
) -> MarkdownNote:
    """
    Synthesize a structured MarkdownNote from raw content using an LLM.

    Builds a prompt by injecting raw_markdown into the template's prompt_template,
    calls the LLM API, and parses the response into a structured MarkdownNote.

    Implements retry logic with exponential backoff for transient API errors.

    Args:
        raw_markdown: The cleaned Markdown content from the de-noiser
        template: The Template to use for structuring the output
        job_id: The Job ID this note belongs to

    Returns:
        MarkdownNote with structured content extracted by the LLM

    Raises:
        AIEngineError: If the LLM API fails after all retry attempts
    """
    # Build prompt from template
    jinja_template = Jinja2Template(template.prompt_template)
    prompt = jinja_template.render(raw_markdown=raw_markdown)

    # Retry logic with exponential backoff
    last_error = None
    for attempt in range(AI_RETRY_COUNT):
        try:
            # Call LLM API
            response = await client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a research assistant that converts web content into structured Markdown notes. Always respond with valid Markdown."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=4000
            )

            # Extract content from response
            content = response.choices[0].message.content

            if not content:
                raise AIEngineError("LLM returned empty content")

            # Parse the MarkdownNote from the LLM response
            note = _parse_markdown_note(content, job_id, template.id)

            return note

        except Exception as e:
            last_error = e

            # If this is the last attempt, raise
            if attempt == AI_RETRY_COUNT - 1:
                break

            # Exponential backoff: 1s, 2s, 4s
            delay = AI_RETRY_BASE_DELAY * (2 ** attempt)
            await asyncio.sleep(delay)

    # All retries exhausted
    raise AIEngineError(
        f"AI synthesis failed after {AI_RETRY_COUNT} attempts. "
        f"Last error: {str(last_error)}"
    )


def _parse_markdown_note(
    content: str,
    job_id: str,
    template_id: str
) -> MarkdownNote:
    """
    Parse LLM output into a MarkdownNote with extracted metadata.

    Extracts title from the first # heading, and tags from the content.
    Falls back to sensible defaults if structure is not as expected.

    Args:
        content: The Markdown content from the LLM
        job_id: The Job ID this note belongs to
        template_id: The template used for synthesis

    Returns:
        MarkdownNote with parsed fields
    """
    # Extract title from first heading
    lines = content.split("\n")
    title = "Untitled Note"

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break

    # Extract tags (look for lines like "Tags: python, api, rest")
    tags = []
    for line in lines:
        lower = line.lower().strip()
        if lower.startswith("tags:") or lower.startswith("**tags:**"):
            # Extract tags from the line
            tag_line = line.split(":", 1)[1] if ":" in line else ""
            tags = [
                tag.strip().strip("*").strip()
                for tag in tag_line.split(",")
                if tag.strip()
            ]
            break

    # Create MarkdownNote
    note = MarkdownNote(
        job_id=job_id,
        title=title,
        content=content,
        template_id=template_id,
        tags=json.dumps(tags),
        version=1  # Will be incremented by worker for re-runs
    )

    return note
