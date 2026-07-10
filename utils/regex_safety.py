"""Bounded regex helpers to limit ReDoS impact on the event loop."""

from __future__ import annotations

import concurrent.futures
import re
from typing import Match, Optional, Pattern

REGEX_TIMEOUT_SECONDS = 1.0
MAX_REGEX_PATTERN_LENGTH = 500
MAX_REGEX_INPUT_LENGTH = 100_000

_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="regex-safe",
)


class RegexTimeoutError(TimeoutError):
    pass


def _bounded_text(text: str) -> str:
    if len(text) > MAX_REGEX_INPUT_LENGTH:
        return text[:MAX_REGEX_INPUT_LENGTH]
    return text


def _validate_pattern(pattern: str) -> None:
    if len(pattern) > MAX_REGEX_PATTERN_LENGTH:
        raise re.error(f"pattern exceeds max length {MAX_REGEX_PATTERN_LENGTH}")


def _run_with_timeout(fn, timeout: float = REGEX_TIMEOUT_SECONDS):
    future = _executor.submit(fn)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError as exc:
        raise RegexTimeoutError(f"regex timed out after {timeout}s") from exc


def safe_re_search(
    pattern: str,
    text: str,
    flags: int = 0,
    timeout: float = REGEX_TIMEOUT_SECONDS,
) -> Optional[Match[str]]:
    _validate_pattern(pattern)
    text = _bounded_text(text)

    def _run():
        return re.search(pattern, text, flags)

    return _run_with_timeout(_run, timeout=timeout)


def safe_re_sub(
    pattern: str,
    repl: str,
    text: str,
    count: int = 0,
    flags: int = 0,
    timeout: float = REGEX_TIMEOUT_SECONDS,
) -> str:
    _validate_pattern(pattern)
    text = _bounded_text(text)

    def _run():
        return re.sub(pattern, repl, text, count=count, flags=flags)

    return _run_with_timeout(_run, timeout=timeout)


def safe_re_finditer(
    pattern: str,
    text: str,
    flags: int = 0,
    timeout: float = REGEX_TIMEOUT_SECONDS,
) -> list[Match[str]]:
    _validate_pattern(pattern)
    text = _bounded_text(text)

    def _run():
        return list(re.finditer(pattern, text, flags))

    return _run_with_timeout(_run, timeout=timeout)


def safe_compile(pattern: str, flags: int = 0) -> Pattern[str]:
    _validate_pattern(pattern)
    return re.compile(pattern, flags)
