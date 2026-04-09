"""
Unit Tests: AI Synthesis Engine

Property 7: AI Engine Receives Content and Template
Validates: Requirements 4.2

Property 8: MarkdownNote Has All Required Fields
Validates: Requirements 4.3

Property 9: LLM Retry Count
Validates: Requirements 4.4
"""

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ai_engine.engine import synthesize, _parse_markdown_note
from ai_engine.exceptions import AIEngineError
from models import Template, MarkdownNote


# Feature: webscribe, Property 7: AI engine receives content and template
@pytest.mark.asyncio
async def test_ai_engine_receives_content_and_template():
    """
    Property: The LLM client is invoked with a prompt containing both raw markdown and template.

    Validates: Requirements 4.2
    """
    raw_markdown = "This is some test content that needs to be processed by the AI engine." * 3
    template_prompt_text = "Please extract key concepts and generate a summary."

    template = Template(
        id="test-template",
        name="Test Template",
        prompt_template=f"Process this content: {{{{ raw_markdown }}}} {template_prompt_text}"
    )

    job_id = "test-job-123"

    # Mock the OpenAI client
    with patch("ai_engine.engine.client") as mock_client:
        # Create mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = f"# Test Title\n\n{raw_markdown[:50]}\n\nTags: test"

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Call synthesize
        await synthesize(raw_markdown, template, job_id)

        # Verify the client was called
        assert mock_client.chat.completions.create.called, "LLM client should be called"

        # Get the call arguments
        call_args = mock_client.chat.completions.create.call_args

        # Extract the user message content
        messages = call_args.kwargs["messages"]
        user_message = next((m for m in messages if m["role"] == "user"), None)

        assert user_message is not None, "Should have user message"

        # Verify both content and template are in the prompt
        prompt_content = user_message["content"]
        assert raw_markdown in prompt_content, "Prompt should contain raw markdown"
        assert template_prompt_text in prompt_content, "Prompt should contain template text"


# Feature: webscribe, Property 8: MarkdownNote has all required fields
@given(
    title=st.text(min_size=5, max_size=50),
    content=st.text(min_size=50, max_size=200),
    tags=st.lists(st.text(min_size=3, max_size=15), min_size=1, max_size=5)
)
@settings(max_examples=100)
def test_markdown_note_has_required_fields(title, content, tags):
    """
    Property: Parsed MarkdownNote has non-empty title, content, and tags fields.

    Validates: Requirements 4.3
    """
    # Create markdown content with proper structure
    tag_line = ", ".join(tags)
    markdown_content = f"# {title}\n\n{content}\n\nTags: {tag_line}"

    note = _parse_markdown_note(
        markdown_content,
        job_id="test-job",
        template_id="test-template"
    )

    # Verify all required fields
    assert note.title, "Title should be non-empty"
    assert note.content, "Content should be non-empty"
    assert note.tags, "Tags should be non-empty"
    assert note.job_id == "test-job", "Job ID should match"
    assert note.template_id == "test-template", "Template ID should match"

    # Verify tags are JSON-encoded
    parsed_tags = json.loads(note.tags)
    assert isinstance(parsed_tags, list), "Tags should be a JSON list"
    assert len(parsed_tags) > 0, "Should have at least one tag"


def test_parse_markdown_note_extracts_title_from_heading():
    """
    Verify that title is extracted from the first # heading.

    Validates: Requirements 4.3
    """
    content = """# My Article Title

This is the content.

Tags: python, web"""

    note = _parse_markdown_note(content, "job-123", "template-123")

    assert note.title == "My Article Title", "Should extract title from first heading"


def test_parse_markdown_note_defaults_to_untitled():
    """
    Verify that title defaults to 'Untitled Note' when no heading is present.

    Validates: Requirements 4.3
    """
    content = "Just some content without a title heading.\n\nTags: test"

    note = _parse_markdown_note(content, "job-123", "template-123")

    assert note.title == "Untitled Note", "Should default to 'Untitled Note'"


def test_parse_markdown_note_extracts_tags():
    """
    Verify that tags are extracted from 'Tags:' line.

    Validates: Requirements 4.3
    """
    content = """# Title

Content here.

Tags: python, api, rest, documentation"""

    note = _parse_markdown_note(content, "job-123", "template-123")

    tags = json.loads(note.tags)
    assert len(tags) == 4, "Should extract 4 tags"
    assert "python" in tags, "Should include 'python' tag"
    assert "api" in tags, "Should include 'api' tag"


# Feature: webscribe, Property 9: LLM retry count
@pytest.mark.asyncio
async def test_llm_retry_count_exactly_three():
    """
    Property: LLM client is called exactly 3 times when it fails every attempt.

    Validates: Requirements 4.4
    """
    template = Template(
        id="test-template",
        name="Test Template",
        prompt_template="Process: {{ raw_markdown }}"
    )

    job_id = "test-job-123"
    raw_markdown = "Test content for retry test. " * 10  # Make it long enough

    # Mock the OpenAI client to always fail
    with patch("ai_engine.engine.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        # Reduce retry delay for faster testing
        with patch("ai_engine.engine.AI_RETRY_BASE_DELAY", 0.01):
            with pytest.raises(AIEngineError) as exc_info:
                await synthesize(raw_markdown, template, job_id)

            # Verify error message mentions retries
            assert "3 attempts" in str(exc_info.value), "Error should mention 3 attempts"

            # Verify the client was called exactly 3 times
            assert mock_client.chat.completions.create.call_count == 3, \
                "Should retry exactly 3 times before failing"


@pytest.mark.asyncio
async def test_llm_succeeds_on_second_attempt():
    """
    Verify that synthesis succeeds if LLM succeeds on a retry attempt.

    Validates: Requirements 4.4
    """
    template = Template(
        id="test-template",
        name="Test Template",
        prompt_template="Process: {{ raw_markdown }}"
    )

    job_id = "test-job-123"
    raw_markdown = "Test content for retry success test. " * 10

    # Mock the OpenAI client to fail once, then succeed
    with patch("ai_engine.engine.client") as mock_client:
        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "# Success\n\nContent\n\nTags: test"

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                Exception("API Error"),  # First attempt fails
                mock_response  # Second attempt succeeds
            ]
        )

        # Reduce retry delay for faster testing
        with patch("ai_engine.engine.AI_RETRY_BASE_DELAY", 0.01):
            # Should succeed without raising
            note = await synthesize(raw_markdown, template, job_id)

            assert note is not None, "Should return a note on retry success"
            assert note.title == "Success", "Should have correct title"

            # Verify the client was called exactly 2 times (fail then success)
            assert mock_client.chat.completions.create.call_count == 2, \
                "Should call LLM twice (one fail, one success)"
