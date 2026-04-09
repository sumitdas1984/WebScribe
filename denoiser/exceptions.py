"""
De-noiser Exceptions

Custom exception classes for content cleaning errors.
"""


class InsufficientContentError(Exception):
    """
    Exception raised when cleaned content is too short to be useful.

    Raised by the de-noiser when the extracted Markdown content
    is fewer than the minimum required characters (default 50),
    indicating that no meaningful content was found on the page.
    """
    pass
