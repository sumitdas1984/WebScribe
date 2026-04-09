"""
Scraper Exceptions

Custom exception classes for scraper error handling.
"""


class ScraperError(Exception):
    """
    Base exception for scraper errors.

    Raised when the scraper encounters an HTTP error (4xx/5xx)
    or other non-timeout failures during page fetching.
    """
    pass


class ScraperTimeoutError(ScraperError):
    """
    Exception raised when a scraper operation exceeds the timeout limit.

    Specifically used by DynamicScraper when page rendering takes
    longer than the configured timeout (default 30 seconds).
    """
    pass
