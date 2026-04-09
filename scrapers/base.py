"""
Base Scraper Interface

Defines the common interface for all scraper implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ScraperResult:
    """
    Result returned by a scraper after fetching a URL.

    Attributes:
        raw_html: The HTML content of the fetched page
        final_url: The final URL after following any redirects
        status_code: HTTP status code of the response
    """
    raw_html: str
    final_url: str
    status_code: int


class BaseScraper(ABC):
    """
    Abstract base class for all scraper implementations.

    Scrapers are responsible for fetching web pages and returning
    their HTML content along with metadata.
    """

    @abstractmethod
    async def fetch(self, url: str) -> ScraperResult:
        """
        Fetch a URL and return its HTML content.

        Args:
            url: The URL to fetch

        Returns:
            ScraperResult containing the page HTML and metadata

        Raises:
            ScraperError: If the fetch fails due to HTTP errors
            ScraperTimeoutError: If the fetch exceeds the timeout limit
        """
        pass
