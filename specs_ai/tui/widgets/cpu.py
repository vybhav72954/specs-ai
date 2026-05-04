"""CPU panel — name, cores/threads, clock, socket, live sparkline."""

from __future__ import annotations

import psutil
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from specs_ai.tui.util import CPU_POLL_INTERVAL


# Braille sparkline characters (8 levels, bottom to top)
_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _sparkline(values: list[float], width: int = 30) -> str:
    """Render a list of 0-100 percentages as a braille sparkline string."""
    if not values:
        return ""
    recent = values[-width:]
    result: list[str] = []
    for v in recent:
        idx = min(int(v / 100 * (len(_SPARK_CHARS) - 1)), len(_SPARK_CHARS) - 1)
        result.append(_SPARK_CHARS[idx])
    return "".join(result)


class CPUPanel(Widget):
    """Displays CPU specs and a live sparkline of CPU usage."""

    DEFAULT_CSS = """
    CPUPanel {
        height: auto;
        border: round #00802080;
        background: #111111;
        padding: 0 1;
    }
    """

    cpu_percent: reactive[float] = reactive(0.0, init=False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: list[float] = []

    def compose(self) -> ComposeResult:
        """Build the CPU info display."""
        yield Static("[b cyan]◉ CPU[/]")
        yield Static("[dim]Scanning...[/]", id="cpu-name")
        yield Static("", id="cpu-cores")
        yield Static("", id="cpu-socket")
        yield Static("", id="cpu-sparkline")

    def on_mount(self) -> None:
        """Start CPU usage polling.

        psutil.cpu_percent(interval=0) returns 0.0 on the very first call
        because there's no prior sample to diff against. We prime it once
        here so the first real poll already has a baseline.
        """
        psutil.cpu_percent(interval=0)
        self.set_interval(CPU_POLL_INTERVAL, self._poll_cpu)

    def _poll_cpu(self) -> None:
        """Sample current CPU usage."""
        self.cpu_percent = psutil.cpu_percent(interval=0)

    def watch_cpu_percent(self, value: float) -> None:
        """React to CPU usage changes — update the sparkline."""
        self._history.append(value)
        if len(self._history) > 30:
            self._history = self._history[-30:]
        spark = _sparkline(self._history)
        try:
            self.query_one("#cpu-sparkline", Static).update(f"  {spark} {value:.0f}%")
        except Exception:
            pass

    def update_data(self, data: dict) -> None:
        """Populate the panel with CPU data."""
        name = data.get("name", "Unknown")
        cores = data.get("physical_cores", "?")
        threads = data.get("logical_cores", "?")
        clock = data.get("max_clock_mhz", "?")
        socket = data.get("socket", "Unknown")

        # Format clock — drop .0
        if isinstance(clock, float) and clock == int(clock):
            clock = int(clock)

        # Socket badge
        if isinstance(socket, str) and socket.upper().startswith("BGA"):
            sock_badge = f"🔒 {socket}"
        elif socket != "Unknown":
            sock_badge = f"🔓 {socket}"
        else:
            sock_badge = socket

        try:
            self.query_one("#cpu-name", Static).update(f"  {name}")
            self.query_one("#cpu-cores", Static).update(f"  {cores}c / {threads}t  max {clock} MHz")
            self.query_one("#cpu-socket", Static).update(f"  Socket: {sock_badge}")
        except Exception:
            pass
