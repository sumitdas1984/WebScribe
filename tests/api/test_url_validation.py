"""
API Tests: URL Validation

Property 1: URL Validation Correctness
Validates: Requirements 1.2, 1.3
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from api.validation import validate_url, validate_urls


# Feature: webscribe, Property 1: URL validation correctness
@given(
    scheme=st.sampled_from(["http", "https"]),
    domain=st.from_regex(r"[a-z0-9-]+\.[a-z]{2,}", fullmatch=True),
    path=st.from_regex(r"(/[a-z0-9-]*)*", fullmatch=True)
)
@settings(max_examples=100)
def test_valid_http_https_urls_pass_validation(scheme, domain, path):
    """
    Property: Well-formed http/https URLs pass validation.

    Validates: Requirements 1.2
    """
    url = f"{scheme}://{domain}{path}"

    is_valid, error = validate_url(url)

    assert is_valid, f"URL {url} should be valid but got error: {error}"
    assert error == "", "Valid URL should have no error message"


@given(
    scheme=st.sampled_from(["ftp", "file", "mailto", "data", "javascript"]),
    domain=st.from_regex(r"[a-z0-9-]+\.[a-z]{2,}", fullmatch=True)
)
@settings(max_examples=100)
def test_non_http_schemes_fail_validation(scheme, domain):
    """
    Property: URLs with non-http/https schemes fail validation.

    Validates: Requirements 1.3
    """
    url = f"{scheme}://{domain}"

    is_valid, error = validate_url(url)

    assert not is_valid, f"URL {url} with scheme {scheme} should be invalid"
    # Error should mention the issue (scheme or malformed)
    assert error, "Invalid URL should have an error message"


def test_specific_valid_urls():
    """
    Test specific examples of valid URLs.

    Validates: Requirements 1.2
    """
    valid_urls = [
        "http://example.com",
        "https://example.com",
        "https://www.example.com",
        "https://subdomain.example.com",
        "https://example.com/path",
        "https://example.com/path/to/page",
        "https://example.com/path?query=value",
        "https://example.com:8080/path",
        "https://example.com#fragment",
    ]

    for url in valid_urls:
        is_valid, error = validate_url(url)
        assert is_valid, f"URL {url} should be valid but got error: {error}"


def test_specific_invalid_urls():
    """
    Test specific examples of invalid URLs.

    Validates: Requirements 1.3
    """
    invalid_urls = [
        ("ftp://example.com", "scheme"),
        ("file:///path/to/file", "scheme"),
        ("not-a-url", "scheme"),
        ("", "scheme"),
        ("http://", "domain"),
        ("javascript:alert(1)", "scheme"),
    ]

    for url, expected_keyword in invalid_urls:
        is_valid, error = validate_url(url)
        assert not is_valid, f"URL {url} should be invalid"
        assert expected_keyword.lower() in error.lower(), \
            f"Error for {url} should mention '{expected_keyword}'"


def test_validate_urls_returns_errors_for_invalid_urls():
    """
    Verify validate_urls returns error details for invalid URLs.

    Validates: Requirements 1.3
    """
    urls = [
        "https://valid.com",
        "ftp://invalid.com",
        "https://also-valid.com",
        "not-a-url"
    ]

    errors = validate_urls(urls)

    # Should have 2 errors
    assert len(errors) == 2, "Should return errors for 2 invalid URLs"

    # Check error structure
    error_urls = [e["url"] for e in errors]
    assert "ftp://invalid.com" in error_urls, "Should flag ftp URL"
    assert "not-a-url" in error_urls, "Should flag malformed URL"

    # Valid URLs should not be in errors
    assert "https://valid.com" not in error_urls
    assert "https://also-valid.com" not in error_urls


def test_validate_urls_returns_empty_list_for_all_valid():
    """
    Verify validate_urls returns empty list when all URLs are valid.

    Validates: Requirements 1.2
    """
    urls = [
        "https://example.com",
        "http://another.com",
        "https://third.com/path"
    ]

    errors = validate_urls(urls)

    assert len(errors) == 0, "Should return no errors for all valid URLs"
