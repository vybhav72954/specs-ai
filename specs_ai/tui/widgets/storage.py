"""Storage panel — physical drives and per-volume usage bars."""

from __future__ import annotations

import psutil
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from specs_ai.tui.util import DISK_POLL_INTERVAL, usage_bar


class StoragePanel(Widget):
    """Displays detected physical drives plus per-mountpoint volume usage.

    Physical drives and logical volumes don't map 1:1 (one disk can host many
    partitions, RAID can span disks), so we render them as two distinct
    sections rather than trying to pair them by index.
    """

    DEFAULT_CSS = """
    StoragePanel {
        height: 100%;
        overflow-y: auto;
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

    def _build_content(self) -> str:
        """Build the full storage panel content from current drives + live volume usage."""
        lines: list[str] = []

        # ── Physical drives (static info from the extractor) ──
        if self._drives:
            for d in self._drives:
                name = d.get("name", "Unknown")
                size = d.get("size_gb", "?")
                dtype = d.get("drive_type", "Unknown")
                if isinstance(size, float) and size == int(size):
                    size = int(size)
                lines.append(f"  {name}")
                lines.append(f"  [dim]{size} GB  │  {dtype}[/]")
        else:
            lines.append("  [dim]No drives detected[/]")

        # ── Volumes (live psutil usage) ──
        try:
            partitions = psutil.disk_partitions(all=False)
        except Exception:
            partitions = []

        if partitions:
            lines.append("")
            lines.append("  [b cyan]Volumes[/]")
            for p in partitions:
                # Skip removable / read-only entries that lack usage info.
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                except (PermissionError, OSError):
                    continue
                pct = usage.percent
                bar = usage_bar(pct, width=10)
                # Strip trailing slash/backslash so "C:\" → "C:"
                label = p.mountpoint.rstrip("\\/").rstrip(":") + ":"
                if pct >= 90:
                    line = f"  {label} [red]{bar}[/]"
                elif pct >= 70:
                    line = f"  {label} [yellow]{bar}[/]"
                else:
                    line = f"  {label} [green]{bar}[/]"
                lines.append(line)

        return "\n".join(lines)

    def _poll_disks(self) -> None:
        """Refresh the live volume-usage portion of the display."""
        try:
            self.query_one("#storage-content", Static).update(self._build_content())
        except Exception:
            pass

    def update_data(self, drives: list) -> None:
        """Populate the panel with physical-drive metadata."""
        self._drives = drives or []
        self._poll_disks()
