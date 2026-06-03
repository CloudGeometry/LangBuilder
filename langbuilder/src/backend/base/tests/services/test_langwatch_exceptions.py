"""Tests for LangWatch exception hierarchy."""
import pytest


def test_langwatch_error_is_importable():
    from langflow.services.langwatch.exceptions import LangWatchError
    assert issubclass(LangWatchError, Exception)


def test_langwatch_key_not_configured_error_is_subclass():
    from langflow.services.langwatch.exceptions import LangWatchError, LangWatchKeyNotConfiguredError
    assert issubclass(LangWatchKeyNotConfiguredError, LangWatchError)


def test_langwatch_invalid_key_error_is_subclass():
    from langflow.services.langwatch.exceptions import LangWatchError, LangWatchInvalidKeyError
    assert issubclass(LangWatchInvalidKeyError, LangWatchError)


def test_langwatch_insufficient_credits_error_is_subclass():
    from langflow.services.langwatch.exceptions import LangWatchError, LangWatchInsufficientCreditsError
    assert issubclass(LangWatchInsufficientCreditsError, LangWatchError)


def test_langwatch_unavailable_error_is_subclass():
    from langflow.services.langwatch.exceptions import LangWatchError, LangWatchUnavailableError
    assert issubclass(LangWatchUnavailableError, LangWatchError)


def test_langwatch_timeout_error_is_subclass():
    from langflow.services.langwatch.exceptions import LangWatchError, LangWatchTimeoutError
    assert issubclass(LangWatchTimeoutError, LangWatchError)


def test_all_exceptions_can_be_raised_and_caught_as_langwatch_error():
    from langflow.services.langwatch.exceptions import (
        LangWatchError,
        LangWatchKeyNotConfiguredError,
        LangWatchInvalidKeyError,
        LangWatchInsufficientCreditsError,
        LangWatchUnavailableError,
        LangWatchTimeoutError,
    )
    exception_classes = [
        LangWatchKeyNotConfiguredError,
        LangWatchInvalidKeyError,
        LangWatchInsufficientCreditsError,
        LangWatchUnavailableError,
        LangWatchTimeoutError,
    ]
    for exc_class in exception_classes:
        with pytest.raises(LangWatchError):
            raise exc_class("test message")


def test_no_circular_imports():
    import importlib
    mod = importlib.import_module("langflow.services.langwatch.exceptions")
    assert mod is not None
