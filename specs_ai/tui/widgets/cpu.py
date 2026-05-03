"""CPU panel — name, cores/threads, clock, socket, live sparkline."""

from __future__ import annotations

import psutil
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from specs_ai.tui.util import fmt


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
    CPUPanel { height: auto; }
    """

    cpu_percent: reactive[float] = reactive(0.0)

    def __init__(self, cpu_data: dict | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data = cpu_data or {}
        self._history: list[float] = []

    def compose(self) -> ComposeResult:
        """Build the CPU info display."""
        d = self._data
        name = d.get("name", "Unknown")
        cores = fmt(d.get("physical_cores", "?"))
        threads = fmt(d.get("logical_cores", "?"))
        clock = fmt(d.get("max_clock_mhz", "?"))
        socket = d.get("socket", "Unknown")

        # Socket badge
        if socket.upper().startswith("BGA"):
            sock_badge = f"🔒 {socket}"
        elif socket != "Unknown":
            sock_badge = f"🔓 {socket}"
        else:
            sock_badge = socket

        yield Static("[b cyan]◉ CPU[/]")
        yield Static(f"  {name}")
        yield Static(f"  {cores}c / {threads}t  max {clock} MHz")
        yield Static(f"  Socket: {sock_badge}")
        yield Static("", id="cpu-sparkline")

    def on_mount(self) -> None:
        """Start CPU usage polling."""
        from specs_ai.tui.util import CPU_POLL_INTERVAL
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

    def update_data(self, cpu_data: dict) -> None:
        """Refresh with new CPU data."""
        self._data = cpu_data
        self._history.clear()
        self.refresh(recompose=True)
