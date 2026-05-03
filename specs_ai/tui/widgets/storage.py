"""Storage panel — drive table with live usage bars."""

from __future__ import annotations

import psutil
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from specs_ai.tui.util import DISK_POLL_INTERVAL, usage_bar, usage_color_class


class StoragePanel(Widget):
    """Displays all detected drives with usage bars."""

    DEFAULT_CSS = """
    StoragePanel {
        height: 100%;
        border: round #00802080;
        background: #111111;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._drives: list = []

    def compose(self) -> ComposeResult:
        """Build the storage display."""
        yield Static("[b cyan]⛁ STORAGE[/]")
        yield Static("[dim]Scanning...[/]", id="storage-content")

    def on_mount(self) -> None:
        """Start disk usage polling."""
        self.set_interval(DISK_POLL_INTERVAL, self._poll_disks)

    def _poll_disks(self) -> None:
        """Update disk usage display."""
        if not self._drives:
            return

        lines: list[str] = []
        partitions = psutil.disk_partitions()

        for i, d in enumerate(self._drives):
            name = d.get("name", "Unknown")
            size = d.get("size_gb", "?")
            dtype = d.get("drive_type", "Unknown")

            if isinstance(size, float) and size == int(size):
                size = int(size)

            lines.append(f"  {name}")
            lines.append(f"  {size} GB  │  {dtype}")

            # Try to get usage for this drive
            if i < len(partitions):
                try:
                    usage = psutil.disk_usage(partitions[i].mountpoint)
                    pct = usage.percent
                    bar = usage_bar(pct)
                    if pct >= 90:
                        lines.append(f"  [red]{bar}[/]")
                    elif pct >= 70:
                        lines.append(f"  [yellow]{bar}[/]")
                    else:
                        lines.append(f"  [green]{bar}[/]")
                except Exception:
                    lines.append("  [dim]Usage unavailable[/]")
            else:
                lines.append("  [dim]Usage unavailable[/]")

            if i < len(self._drives) - 1:
                lines.append("")

        try:
            self.query_one("#storage-content", Static).update("\n".join(lines))
        except Exception:
            pass

    def update_data(self, drives: list) -> None:
        """Populate the panel with drive data."""
        self._drives = drives or []

        if not self._drives:
            try:
                self.query_one("#storage-content", Static).update("[dim]No drives detected[/]")
            except Exception:
                pass
            return

        # Initial display (before polling kicks in)
        lines: list[str] = []
        for i, d in enumerate(self._drives):
            name = d.get("name", "Unknown")
            size = d.get("size_gb", "?")
            dtype = d.get("drive_type", "Unknown")
            if isinstance(size, float) and size == int(size):
                size = int(size)
            lines.append(f"  {name}")
            lines.append(f"  {size} GB  │  {dtype}")
            if i < len(self._drives) - 1:
                lines.append("")

        try:
            self.query_one("#storage-content", Static).update("\n".join(lines))
        except Exception:
            pass

        # Trigger an immediate poll
        self._poll_disks()
