"""Storage panel — drive table with live usage bars."""

from __future__ import annotations

import psutil
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from specs_ai.tui.util import fmt, usage_bar, usage_color_class


class StoragePanel(Widget):
    """Displays all detected drives with usage bars."""

    DEFAULT_CSS = """
    StoragePanel { height: auto; }
    """

    def __init__(self, drives_data: list | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._drives = drives_data or []

    def compose(self) -> ComposeResult:
        """Build the storage display."""
        yield Static("[b cyan]⛁ STORAGE[/]")

        if not self._drives:
            yield Static("  [dim]No drives detected[/]")
            return

        for i, d in enumerate(self._drives):
            name = d.get("name", "Unknown")
            size = fmt(d.get("size_gb", "?"))
            dtype = d.get("drive_type", "Unknown")
            yield Static(f"  {name}")
            yield Static(f"  {size} GB  │  {dtype}")
            yield Static("", id=f"drive-bar-{i}")

    def on_mount(self) -> None:
        """Start disk usage polling."""
        from specs_ai.tui.util import DISK_POLL_INTERVAL
        self.set_interval(DISK_POLL_INTERVAL, self._poll_disks)
        self._poll_disks()

    def _poll_disks(self) -> None:
        """Update disk usage bars for mounted partitions."""
        partitions = psutil.disk_partitions()
        for i, _drive in enumerate(self._drives):
            try:
                bar_widget = self.query_one(f"#drive-bar-{i}", Static)
            except Exception:
                continue

            # Try to match the drive to a mounted partition
            if i < len(partitions):
                try:
                    usage = psutil.disk_usage(partitions[i].mountpoint)
                    pct = usage.percent
                    bar = usage_bar(pct)
                    color = usage_color_class(pct, low=70.0, high=90.0)
                    bar_widget.update(f"  {bar}")
                    bar_widget.remove_class("status-green", "status-amber", "status-red")
                    bar_widget.add_class(color)
                except Exception:
                    bar_widget.update("  [dim]Usage unavailable[/]")
            else:
                bar_widget.update("  [dim]Usage unavailable[/]")

    def update_data(self, drives_data: list) -> None:
        """Refresh with new drive data."""
        self._drives = drives_data
        self.refresh(recompose=True)
