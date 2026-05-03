"""Shared TUI utilities — formatters, color helpers, constants."""

from __future__ import annotations

# ── Live polling intervals (seconds) ──────────────────────────
CPU_POLL_INTERVAL = 1.0
RAM_POLL_INTERVAL = 2.0
DISK_POLL_INTERVAL = 5.0

# ── Uptime thresholds (seconds) ───────────────────────────────
UPTIME_WARN_SECS = 5 * 86400    # 5 days
UPTIME_CRIT_SECS = 15 * 86400   # 15 days


def fmt(value: int | float | str | None, suffix: str = "") -> str:
    """Format a hardware value for display. Drops '.0' from whole floats."""
    if value is None or value == "Unknown":
        return "Unknown"
    if isinstance(value, float) and value == int(value):
        return f"{int(value)}{suffix}"
    return f"{value}{suffix}"


def usage_bar(percent: float, width: int = 16) -> str:
    """Return a text-based usage bar like '████████░░░░ 62%'."""
    filled = int(percent / 100 * width)
    empty = width - filled
    return f"{'█' * filled}{'░' * empty} {percent:.0f}%"


def usage_color_class(percent: float, low: float = 60.0, high: float = 85.0) -> str:
    """Return a CSS class name based on usage percentage thresholds."""
    if percent >= high:
        return "status-red"
    if percent >= low:
        return "status-amber"
    return "status-green"
