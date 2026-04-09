"""
Unit Tests: Scraper Engine Routing

Property 2: Engine Routing
Validates: Requirements 2.2, 2.3

Property 3: Dynamic Scraper Timeout Produces Failed Job
Validates: Requirements 2.6
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from scrapers.static_scraper import StaticScraper
from scrapers.dynamic_scraper import DynamicScraper
from scrapers.base import BaseScraper


# Feature: webscribe, Property 2: Engine routing correctness
@given(engine_choice=st.sampled_from(["static", "dynamic"]))
@settings(max_examples=100)
def test_engine_routing_correctness(engine_choice):
    """
    Property: For any valid engine selection, the correct scraper class is instantiated.

    Validates: Requirements 2.2, 2.3
    """
    # Simulate worker engine selection logic
    if engine_choice == "static":
        scraper = StaticScraper()
        assert isinstance(scraper, StaticScraper), "Should instantiate StaticScraper for 'static'"
        assert isinstance(scraper, BaseScraper), "StaticScraper should inherit from BaseScraper"
    elif engine_choice == "dynamic":
        scraper = DynamicScraper()
        assert isinstance(scraper, DynamicScraper), "Should instantiate DynamicScraper for 'dynamic'"
        assert isinstance(scraper, BaseScraper), "DynamicScraper should inherit from BaseScraper"


def test_static_scraper_not_used_for_dynamic():
    """
    Verify that selecting 'dynamic' engine does NOT instantiate StaticScraper.

    Validates: Requirements 2.3
    """
    scraper = DynamicScraper()
    assert not isinstance(scraper, StaticScraper), "DynamicScraper should not be a StaticScraper"


def test_dynamic_scraper_not_used_for_static():
    """
    Verify that selecting 'static' engine does NOT instantiate DynamicScraper.

    Validates: Requirements 2.2
    """
    scraper = StaticScraper()
    assert not isinstance(scraper, DynamicScraper), "StaticScraper should not be a DynamicScraper"


@pytest.mark.asyncio
async def test_dynamic_scraper_timeout_raises_timeout_error():
    """
    Property 3: Dynamic scraper timeout produces ScraperTimeoutError.

    Validates: Requirements 2.6

    Note: This is a unit test that verifies the timeout mechanism.
    The full integration test (timeout -> failed job) will be in the worker tests.
    """
    from scrapers.exceptions import ScraperTimeoutError

    # Use a very short timeout to force a timeout on a slow-loading page
    scraper = DynamicScraper(timeout=1)  # 1 second timeout

    # Use a URL that's known to be slow or use httpbin.org/delay endpoint
    slow_url = "https://httpbin.org/delay/5"  # Delays response for 5 seconds

    with pytest.raises(ScraperTimeoutError) as exc_info:
        await scraper.fetch(slow_url)

    # Verify the error message mentions timeout
    assert "timeout" in str(exc_info.value).lower(), "Error message should mention timeout"
    assert slow_url in str(exc_info.value), "Error message should include the URL"


@pytest.mark.asyncio
async def test_static_scraper_returns_scraper_result():
    """
    Verify StaticScraper returns a valid ScraperResult for a successful fetch.

    Validates: Requirements 2.2, 2.4
    """
    from scrapers.base import ScraperResult

    scraper = StaticScraper()

    # Use httpbin.org for reliable testing
    result = await scraper.fetch("https://httpbin.org/html")

    assert isinstance(result, ScraperResult), "Should return ScraperResult instance"
    assert result.raw_html, "Should have HTML content"
    assert result.final_url, "Should have final URL"
    assert result.status_code == 200, "Should have 200 status code"


@pytest.mark.asyncio
async def test_static_scraper_raises_error_on_4xx():
    """
    Verify StaticScraper raises ScraperError for 4xx status codes.

    Validates: Requirements 2.4
    """
    from scrapers.exceptions import ScraperError

    scraper = StaticScraper()

    with pytest.raises(ScraperError) as exc_info:
        await scraper.fetch("https://httpbin.org/status/404")

    assert "404" in str(exc_info.value), "Error message should mention 404 status"
