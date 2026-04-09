"""
Static Scraper Implementation

Uses httpx to fetch static HTML pages without JavaScript rendering.
Fast and lightweight for simple pages.
"""

import httpx

from config import STATIC_SCRAPER_TIMEOUT
from scrapers.base import BaseScraper, ScraperResult
from scrapers.exceptions import ScraperError


class StaticScraper(BaseScraper):
    """
    Scraper for static HTML pages using httpx.

    Best for:
    - Blogs and articles with server-rendered HTML
    - Pages without JavaScript-dependent content
    - Fast scraping where JS execution is not needed

    Limitations:
    - Cannot execute JavaScript
    - Won't see dynamically loaded content
    - May miss content rendered client-side
    """

    def __init__(self, timeout: int = STATIC_SCRAPER_TIMEOUT):
        """
        Initialize the static scraper.

        Args:
            timeout: Request timeout in seconds (default from config)
        """
        self.timeout = timeout

    async def fetch(self, url: str) -> ScraperResult:
        """
        Fetch a URL using httpx and return the HTML content.

        Args:
            url: The URL to fetch

        Returns:
            ScraperResult containing the page HTML and metadata

        Raises:
            ScraperError: If the request fails or returns a 4xx/5xx status
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)

                # Raise on 4xx/5xx status codes
                if response.status_code >= 400:
                    raise ScraperError(
                        f"HTTP {response.status_code} error fetching {url}: {response.reason_phrase}"
                    )

                return ScraperResult(
                    raw_html=response.text,
                    final_url=str(response.url),
                    status_code=response.status_code
                )

        except httpx.TimeoutException as e:
            raise ScraperError(f"Request timeout fetching {url}: {str(e)}")

        except httpx.RequestError as e:
            raise ScraperError(f"Request error fetching {url}: {str(e)}")

        except Exception as e:
            raise ScraperError(f"Unexpected error fetching {url}: {str(e)}")
