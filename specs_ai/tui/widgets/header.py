"""Header widget — block-letter title, hostname, uptime clock, wall clock."""

import platform
import time
from datetime import datetime

import psutil
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


TITLE_ART = """\
███████╗██████╗ ███████╗ ██████╗███████╗       █████╗ ██╗
██╔════╝██╔══██╗██╔════╝██╔════╝██╔════╝      ██╔══██╗██║
███████╗██████╔╝█████╗  ██║     ███████╗█████╗███████║██║
╚════██║██╔═══╝ ██╔══╝  ██║     ╚════██║╚════╝██╔══██║██║
███████║██║     ███████╗╚██████╗███████║      ██║  ██║██║
╚══════╝╚═╝     ╚══════╝ ╚═════╝╚══════╝      ╚═╝  ╚═╝╚═╝"""


class HeaderWidget(Widget):
    """Top bar: block-letter SPECS-AI title and live subtitle row."""

    uptime_seconds: reactive[int] = reactive(0, init=False)
    clock_text: reactive[str] = reactive("", init=False)

    def __init__(self, initial_uptime: int = 0, **kwargs) -> None:
        super().__init__(**kwargs)
        # Cache the boot timestamp once so each tick reads a real wall-clock
        # delta rather than incrementing a counter (which would drift away
        # from psutil during long-running sessions or slow first-paint).
        try:
            self._boot_ts: float | None = float(psutil.boot_time())
        except Exception:
            self._boot_ts = None
        # Kept for API compatibility; if psutil failed we'll fall back to
        # the value passed in by the app once it has scanned hardware.
        self._initial_uptime = initial_uptime

    def compose(self) -> ComposeResult:
        """Build the header layout."""
        yield Static(TITLE_ART, id="title-art")
        with Horizontal(id="subtitle-bar"):
            yield Static(f"  {platform.node()}", classes="subtitle-item")
            yield Static("", id="uptime-label", classes="subtitle-item")
            yield Static("", id="clock-label", classes="subtitle-item-right")

    def on_mount(self) -> None:
        """Start the 1-second timer for clock and uptime ticks."""
        self._tick()
        self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        """Update uptime and wall clock every second."""
        if self._boot_ts is not None:
            self.uptime_seconds = max(0, int(time.time() - self._boot_ts))
        else:
            # psutil unavailable — fall back to incrementing from the
            # initial seed; less accurate but doesn't drift visibly within
            # a single session.
            self.uptime_seconds += 1
        self.clock_text = datetime.now().strftime("%H:%M:%S")

    def watch_uptime_seconds(self, value: int) -> None:
        """React to uptime changes — update display and color."""
        try:
            label = self.query_one("#uptime-label", Static)
        except Exception:
            return
        formatted = self._format_uptime(value)
        days = value // 86400

        if days >= 15:
            color_class = "status-red"
        elif days >= 5:
            color_class = "status-amber"
        else:
            color_class = "status-green"

        label.update(f"▲ {formatted}")
        label.remove_class("status-green", "status-amber", "status-red")
        label.add_class(color_class)

    def watch_clock_text(self, value: str) -> None:
        """React to clock changes."""
        try:
            self.query_one("#clock-label", Static).update(value)
        except Exception:
            pass

    @staticmethod
    def _format_uptime(seconds: int) -> str:
        """Convert seconds to 'Xd Yh Zm Ws' string."""
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)
        parts: list[str] = []
        if days:
            parts.append(f"{days}d")
        if hours or days:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        parts.append(f"{secs:02d}s")
        return " ".join(parts)
