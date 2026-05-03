"""RAM panel — total, type, speed, slots, live usage bar."""

from __future__ import annotations

import psutil
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from specs_ai.tui.util import fmt, usage_bar, usage_color_class


class RAMPanel(Widget):
    """Displays RAM specs and a live memory usage bar."""

    DEFAULT_CSS = """
    RAMPanel { height: auto; }
    """

    ram_percent: reactive[float] = reactive(0.0)

    def __init__(self, ram_data: dict | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data = ram_data or {}

    def compose(self) -> ComposeResult:
        """Build the RAM info display."""
        d = self._data
        total = fmt(d.get("total_gb", "?"))
        ram_type = d.get("ram_type", "Unknown")
        speed = fmt(d.get("speed_mhz", "?"))
        slots = fmt(d.get("slots_used", "?"))

        type_str = f" {ram_type}" if ram_type and ram_type != "Unknown" else ""

        yield Static("[b cyan]▦ RAM[/]")
        yield Static(f"  {total} GB{type_str}")
        yield Static(f"  {speed} MHz  ({slots} slot(s))")
        yield Static("", id="ram-usage-bar")

    def on_mount(self) -> None:
        """Start RAM usage polling."""
        from specs_ai.tui.util import RAM_POLL_INTERVAL
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

    def update_data(self, ram_data: dict) -> None:
        """Refresh with new RAM data."""
        self._data = ram_data
        self.refresh(recompose=True)
