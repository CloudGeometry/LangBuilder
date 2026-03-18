"""LangWatch service exception hierarchy.

These exceptions are raised by LangWatchService and caught by the
usage router, which maps them to structured HTTP error responses.
"""


class LangWatchError(Exception):
    """Base class for all LangWatch service errors."""



class LangWatchKeyNotConfiguredError(LangWatchError):
    """No LangWatch API key is stored in GlobalSettings.

    HTTP mapping: 503 KEY_NOT_CONFIGURED
    """



class LangWatchInvalidKeyError(LangWatchError):
    """LangWatch returned 401 with an 'invalid key' body.

    HTTP mapping: 422 INVALID_KEY
    """



class LangWatchInsufficientCreditsError(LangWatchError):
    """LangWatch returned 401 with an 'insufficient credits' body.

    HTTP mapping: 422 INSUFFICIENT_CREDITS
    """



class LangWatchConnectionError(LangWatchError):
    """LangWatch could not be reached due to a network error or timeout.

    HTTP mapping: 503 LANGWATCH_UNAVAILABLE
    """



class LangWatchUnavailableError(LangWatchError):
    """LangWatch returned 5xx or a connection error occurred.

    HTTP mapping: 503 LANGWATCH_UNAVAILABLE
    """



class LangWatchTimeoutError(LangWatchError):
    """LangWatch did not respond within the configured timeout.

    HTTP mapping: 503 LANGWATCH_TIMEOUT
    """

