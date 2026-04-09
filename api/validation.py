"""
API Validation Utilities

URL validation and input sanitization.
"""

from urllib.parse import urlparse
from typing import List, Tuple


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate that a URL is well-formed and uses http/https scheme.

    Args:
        url: The URL string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, error_message) if invalid
    """
    try:
        parsed = urlparse(url)

        # Check scheme is http or https
        if parsed.scheme not in ["http", "https"]:
            return False, f"Invalid URL scheme '{parsed.scheme}'. Only http and https are supported."

        # Check netloc (domain) is present
        if not parsed.netloc:
            return False, "URL must have a domain (e.g., example.com)"

        return True, ""

    except Exception as e:
        return False, f"Malformed URL: {str(e)}"


def validate_urls(urls: List[str]) -> List[dict]:
    """
    Validate multiple URLs and return error details for invalid ones.

    Args:
        urls: List of URL strings to validate

    Returns:
        List of error dictionaries for invalid URLs.
        Empty list if all URLs are valid.

    Example:
        >>> validate_urls(["https://example.com", "ftp://bad.com"])
        [{"url": "ftp://bad.com", "error": "Invalid URL scheme..."}]
    """
    errors = []

    for url in urls:
        is_valid, error_message = validate_url(url)
        if not is_valid:
            errors.append({
                "url": url,
                "error": error_message
            })

    return errors
