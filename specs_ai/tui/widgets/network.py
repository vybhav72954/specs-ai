"""Network panel — WiFi adapter name and live connection status."""

from __future__ import annotations

import psutil
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


# Substrings that identify a WiFi interface in psutil's friendly name.
_WIFI_NAME_KEYWORDS: tuple[str, ...] = ("wi-fi", "wifi", "wireless", "wlan")

# Poll the live status every 5s — connection state changes are rare.
_NET_POLL_INTERVAL = 5.0


def _wifi_link_status() -> tuple[bool, int | None]:
    """Return (is_up, speed_mbps) for the first matching WiFi interface.

    Falls back to (False, None) when no WiFi interface is found.
    """
    try:
        stats = psutil.net_if_stats()
    except Exception:
        return False, None

    for name, st in stats.items():
        lname = name.lower()
        if any(kw in lname for kw in _WIFI_NAME_KEYWORDS):
            return bool(st.isup), int(st.speed) if st.speed else None

    return False, None


class NetworkPanel(Widget):
    """Displays the primary WiFi adapter and its live up/down state."""

    DEFAULT_CSS = """
    NetworkPanel {
        height: auto;
        border: round #00802080;
        background: #111111;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._adapter_name: str = "Unknown"

    def compose(self) -> ComposeResult:
        """Build the network info display."""
        yield Static("[b cyan]⚡ NETWORK[/]")
        yield Static("[dim]Scanning...[/]", id="net-name")
        yield Static("", id="net-status")

    def on_mount(self) -> None:
        """Start polling live link status."""
        self.set_interval(_NET_POLL_INTERVAL, self._refresh_status)

    def _refresh_status(self) -> None:
        """Refresh the connection-status line based on psutil link state."""
        try:
            label = self.query_one("#net-status", Static)
        except Exception:
            return

        if not self._adapter_name or self._adapter_name == "Unknown":
            label.update("  [dim]○ No adapter[/]")
            return

        is_up, speed = _wifi_link_status()
        if is_up:
            speed_part = f"  ({speed} Mb/s)" if speed else ""
            label.update(f"  [green]● Connected[/]{speed_part}")
        else:
            label.update("  [yellow]◌ Down[/]")

    def update_data(self, data: dict) -> None:
        """Populate the panel with WiFi adapter metadata."""
        self._adapter_name = data.get("name", "Unknown") or "Unknown"
        try:
            self.query_one("#net-name", Static).update(f"  {self._adapter_name}")
        except Exception:
            pass
        self._refresh_status()
