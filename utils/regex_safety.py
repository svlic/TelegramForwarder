"""Bounded regex helpers to limit ReDoS impact on the event loop.

Uses a child process so catastrophic patterns can be terminated on timeout.
Thread pools cannot kill a stuck re engine; process isolation can.
"""

from __future__ import annotations

import multiprocessing as mp
import re
from dataclasses import dataclass
from typing import Match, Optional, Pattern, Tuple

REGEX_TIMEOUT_SECONDS = 1.0
MAX_REGEX_PATTERN_LENGTH = 500
MAX_REGEX_INPUT_LENGTH = 100_000

try:
    _MP_CTX = mp.get_context("fork")
except ValueError:
    _MP_CTX = mp.get_context("spawn")


class RegexTimeoutError(TimeoutError):
    pass


@dataclass(frozen=True)
class _MatchData:
    group0: str
    span: Tuple[int, int]
    groups: Tuple[str | None, ...]

    def group(self, index: int = 0) -> str | None:
        if index == 0:
            return self.group0
        if index < 0 or index > len(self.groups):
            raise IndexError("no such group")
        return self.groups[index - 1]

    def start(self, group: int = 0) -> int:
        if group != 0:
            raise IndexError("only group 0 span is available")
        return self.span[0]

    def end(self, group: int = 0) -> int:
        if group != 0:
            raise IndexError("only group 0 span is available")
        return self.span[1]


def _bounded_text(text: str) -> str:
    if len(text) > MAX_REGEX_INPUT_LENGTH:
        return text[:MAX_REGEX_INPUT_LENGTH]
    return text


def _validate_pattern(pattern: str) -> None:
    if len(pattern) > MAX_REGEX_PATTERN_LENGTH:
        raise re.error(f"pattern exceeds max length {MAX_REGEX_PATTERN_LENGTH}")


def _match_to_data(match: Match[str] | None) -> _MatchData | None:
    if match is None:
        return None
    return _MatchData(
        group0=match.group(0),
        span=match.span(0),
        groups=match.groups(),
    )


def _regex_worker(
    conn,
    op: str,
    pattern: str,
    text: str,
    flags: int,
    repl: str,
    count: int,
) -> None:
    try:
        if op == "search":
            result = _match_to_data(re.search(pattern, text, flags))
        elif op == "sub":
            result = re.sub(pattern, repl, text, count=count, flags=flags)
        elif op == "finditer":
            result = [_match_to_data(m) for m in re.finditer(pattern, text, flags)]
        else:
            raise ValueError(f"unknown regex op: {op}")
        conn.send(("ok", result))
    except Exception as exc:
        conn.send(("err", type(exc).__name__, str(exc)))
    finally:
        conn.close()


def _run_with_timeout(
    op: str,
    pattern: str,
    text: str,
    *,
    flags: int = 0,
    repl: str = "",
    count: int = 0,
    timeout: float = REGEX_TIMEOUT_SECONDS,
):
    parent_conn, child_conn = _MP_CTX.Pipe(duplex=False)
    proc = _MP_CTX.Process(
        target=_regex_worker,
        args=(child_conn, op, pattern, text, flags, repl, count),
        daemon=True,
    )
    proc.start()
    child_conn.close()
    try:
        if not parent_conn.poll(timeout):
            proc.terminate()
            proc.join(1.0)
            if proc.is_alive():
                proc.kill()
                proc.join(1.0)
            raise RegexTimeoutError(f"regex timed out after {timeout}s")

        status, *payload = parent_conn.recv()
        if status == "ok":
            return payload[0]
        exc_name, exc_msg = payload
        if exc_name in ("error", "re.error"):
            raise re.error(exc_msg)
        raise RuntimeError(f"regex worker failed ({exc_name}): {exc_msg}")
    finally:
        parent_conn.close()
        if proc.is_alive():
            proc.terminate()
            proc.join(1.0)
            if proc.is_alive():
                proc.kill()
                proc.join(1.0)


def safe_re_search(
    pattern: str,
    text: str,
    flags: int = 0,
    timeout: float = REGEX_TIMEOUT_SECONDS,
) -> Optional[_MatchData]:
    _validate_pattern(pattern)
    text = _bounded_text(text)
    return _run_with_timeout("search", pattern, text, flags=flags, timeout=timeout)


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
    return _run_with_timeout(
        "sub",
        pattern,
        text,
        flags=flags,
        repl=repl,
        count=count,
        timeout=timeout,
    )


def safe_re_finditer(
    pattern: str,
    text: str,
    flags: int = 0,
    timeout: float = REGEX_TIMEOUT_SECONDS,
) -> list[_MatchData]:
    _validate_pattern(pattern)
    text = _bounded_text(text)
    result = _run_with_timeout("finditer", pattern, text, flags=flags, timeout=timeout)
    return list(result or [])


def safe_compile(pattern: str, flags: int = 0) -> Pattern[str]:
    _validate_pattern(pattern)
    return re.compile(pattern, flags)
