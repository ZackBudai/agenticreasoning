"""Shared deadline helper for hard per-goal timeout enforcement.

Cooperative checks only — Python can't kill a running thread — but every
LLM/Isabelle call is bounded by `remaining_int(...)`, so worst-case overrun is
bounded by one in-flight subordinate timeout.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


class DeadlineExceeded(TimeoutError):
    """Raised when the per-goal budget is exhausted."""


@dataclass(slots=True)
class Deadline:
    """Absolute-time per-goal deadline.

    Use `remaining_int(cap)` to derive timeouts for subordinate calls
    (LLM HTTP, Isabelle theory runs) so they never extend past the deadline.
    Use `expired()` / `check()` at loop boundaries and between LLM calls.
    """
    timeout_s: float
    t0: float = field(default_factory=time.monotonic)

    def remaining(self) -> float:
        return max(0.0, self.timeout_s - (time.monotonic() - self.t0))

    def remaining_int(self, cap: int | float | None = None, min_: int = 1) -> int:
        """Return seconds remaining, clamped to [min_, cap] (cap optional)."""
        r = self.remaining()
        if cap is not None:
            r = min(r, float(cap))
        return max(int(min_), int(r))

    def expired(self) -> bool:
        return self.remaining() <= 0.0

    def check(self) -> None:
        if self.expired():
            raise DeadlineExceeded(
                f"deadline exceeded after {time.monotonic() - self.t0:.1f}s "
                f"(budget {self.timeout_s:.1f}s)"
            )
