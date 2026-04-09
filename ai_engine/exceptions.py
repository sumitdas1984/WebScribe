"""
AI Engine Exceptions

Custom exception classes for AI synthesis errors.
"""


class AIEngineError(Exception):
    """
    Exception raised when the AI engine fails to synthesize content.

    Raised after exhausting all retry attempts when the LLM API
    returns errors or fails to produce valid output.
    """
    pass
