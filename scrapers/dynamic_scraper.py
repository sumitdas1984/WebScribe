"""
Dynamic Scraper Implementation

Uses Playwright to render JavaScript-heavy pages in a real browser.
Slower but handles dynamic content that requires JS execution.
"""

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from config import DYNAMIC_SCRAPER_TIMEOUT
from scrapers.base import BaseScraper, ScraperResult
from scrapers.exceptions import ScraperError, ScraperTimeoutError


class DynamicScraper(BaseScraper):
    """
    Scraper for JavaScript-rendered pages using Playwright.

    Best for:
    - Single-page applications (SPAs)
    - Pages with content loaded via AJAX/fetch
    - JavaScript-heavy sites where static scraping misses content

    Trade-offs:
    - Slower than static scraping (browser overhead)
    - Higher resource usage (runs real browser)
    - 30-second timeout enforced to prevent hanging
    """

    def __init__(self, timeout: int = DYNAMIC_SCRAPER_TIMEOUT):
        """
        Initialize the dynamic scraper.

        Args:
            timeout: Page load timeout in seconds (default from config)
        """
        self.timeout = timeout * 1000  # Convert to milliseconds for Playwright

    async def fetch(self, url: str) -> ScraperResult:
        """
        Fetch a URL using Playwright and return the fully rendered HTML.

        Launches a headless Chromium browser, navigates to the URL,
        waits for the network to be idle, and extracts the final HTML.

        Args:
            url: The URL to fetch

        Returns:
            ScraperResult containing the rendered HTML and metadata

        Raises:
            ScraperTimeoutError: If page load exceeds the timeout
            ScraperError: If the browser operation fails
        """
        try:
            async with async_playwright() as p:
                # Launch headless browser
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                try:
                    # Navigate to URL and wait for network idle
                    response = await page.goto(
                        url,
                        wait_until="networkidle",
                        timeout=self.timeout
                    )

                    if response is None:
                        raise ScraperError(f"Failed to load {url}: no response received")

                    # Extract the fully rendered HTML
                    raw_html = await page.content()
                    final_url = page.url
                    status_code = response.status

                    return ScraperResult(
                        raw_html=raw_html,
                        final_url=final_url,
                        status_code=status_code
                    )

                except PlaywrightTimeoutError:
                    raise ScraperTimeoutError(
                        f"Page load timeout ({self.timeout / 1000}s) exceeded for {url}"
                    )

                finally:
                    await context.close()
                    await browser.close()

        except ScraperTimeoutError:
            # Re-raise timeout errors as-is
            raise

        except Exception as e:
            if isinstance(e, ScraperError):
                raise
            raise ScraperError(f"Browser error fetching {url}: {str(e)}")
