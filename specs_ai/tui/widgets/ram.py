"""RAM panel — total, type, speed, slots, live usage bar."""

from __future__ import annotations

import psutil
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from specs_ai.tui.util import RAM_POLL_INTERVAL, usage_bar, usage_color_class


class RAMPanel(Widget):
    """Displays RAM specs and a live memory usage bar."""

    DEFAULT_CSS = """
    RAMPanel {
        height: 100%;
        border: round #00802080;
        background: #111111;
        padding: 0 1;
    }
    """

    ram_percent: reactive[float] = reactive(0.0, init=False)

    def compose(self) -> ComposeResult:
        """Build the RAM info display."""
        yield Static("[b cyan]▦ RAM[/]")
        yield Static("[dim]Scanning...[/]", id="ram-total")
        yield Static("", id="ram-speed")
        yield Static("", id="ram-usage-bar")

    def on_mount(self) -> None:
        """Start RAM usage polling."""
        self.set_interval(RAM_POLL_INTERVAL, self._poll_ram)
        self._poll_ram()

    def _poll_ram(self) -> None:
        """Sample current RAM usage."""
        mem = psutil.virtual_memory()
        self.ram_percent = mem.percent

    def watch_ram_percent(self, value: float) -> None:
        """React to RAM usage changes — update the bar."""
        bar = usage_bar(value)
        color = usage_color_class(value)
        used_gb = psutil.virtual_memory().used / (1024 ** 3)
        total_gb = psutil.virtual_memory().total / (1024 ** 3)
        try:
            label = self.query_one("#ram-usage-bar", Static)
            label.update(f"  {bar}\n  {used_gb:.1f} / {total_gb:.1f} GB used")
            label.remove_class("status-green", "status-amber", "status-red")
            label.add_class(color)
        except Exception:
            pass

    def update_data(self, data: dict) -> None:
        """Populate the panel with RAM data."""
        total = data.get("total_gb", "?")
        ram_type = data.get("ram_type", "Unknown")
        speed = data.get("speed_mhz", "?")
        slots = data.get("slots_used", "?")

        # Format values — drop .0
        if isinstance(total, float) and total == int(total):
            total = int(total)
        if isinstance(speed, float) and speed == int(speed):
            speed = int(speed)

        type_str = f" {ram_type}" if ram_type and ram_type != "Unknown" else ""

        try:
            self.query_one("#ram-total", Static).update(f"  {total} GB{type_str}")
            self.query_one("#ram-speed", Static).update(f"  {speed} MHz  ({slots} slot(s))")
        except Exception:
            pass
