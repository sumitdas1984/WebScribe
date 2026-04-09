"""
HTML De-noiser

Extracts meaningful content from HTML and converts it to clean Markdown.
Removes navigation, ads, headers, footers, and other non-content elements.
"""

import re
from bs4 import BeautifulSoup
from markdownify import markdownify

from config import MIN_CONTENT_LENGTH
from denoiser.exceptions import InsufficientContentError


def clean(raw_html: str) -> str:
    """
    Clean HTML and convert to structured Markdown.

    Algorithm:
    1. Parse HTML with BeautifulSoup (lxml parser)
    2. Select content root: <main>, <article>, or <body> (in that order)
    3. Remove noise elements: header, footer, nav, aside, script, style
    4. Convert remaining HTML to Markdown preserving structure
    5. Normalize whitespace and collapse excessive blank lines

    Args:
        raw_html: Raw HTML content from the scraper

    Returns:
        Clean Markdown string with preserved structure

    Raises:
        InsufficientContentError: If the result is fewer than MIN_CONTENT_LENGTH characters
    """
    # Parse HTML with lxml parser for better performance
    soup = BeautifulSoup(raw_html, "lxml")

    # Select content root: prefer <main> or <article>, fall back to <body>
    content_root = (
        soup.find("main")
        or soup.find("article")
        or soup.find("body")
        or soup  # Fallback to entire document if no body
    )

    # Remove noise elements
    noise_tags = ["header", "footer", "nav", "aside", "script", "style"]
    for tag_name in noise_tags:
        for tag in content_root.find_all(tag_name):
            tag.decompose()

    # Convert to Markdown preserving structure
    markdown_content = markdownify(
        str(content_root),
        heading_style="ATX",  # Use # for headings
        bullets="-",  # Use - for unordered lists
        code_language_callback=lambda el: el.get("class", [""])[0].replace("language-", "")
        if el.get("class")
        else "",
    )

    # Normalize whitespace
    # 1. Strip leading/trailing whitespace
    markdown_content = markdown_content.strip()

    # 2. Collapse 3+ consecutive blank lines to exactly 2
    markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

    # 3. Remove excessive spaces within lines
    markdown_content = re.sub(r" {2,}", " ", markdown_content)

    # Validate content length
    if len(markdown_content) < MIN_CONTENT_LENGTH:
        raise InsufficientContentError(
            f"Extracted content is only {len(markdown_content)} characters "
            f"(minimum: {MIN_CONTENT_LENGTH}). No meaningful content found."
        )

    return markdown_content
