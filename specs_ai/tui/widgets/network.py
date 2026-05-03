"""Network panel — WiFi adapter name and connection status."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class NetworkPanel(Widget):
    """Displays WiFi adapter information."""

    DEFAULT_CSS = """
    NetworkPanel { height: auto; }
    """

    def __init__(self, wifi_data: dict | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data = wifi_data or {}

    def compose(self) -> ComposeResult:
        """Build the network info display."""
        name = self._data.get("name", "Unknown")

        yield Static("[b cyan]⚡ NETWORK[/]")
        yield Static(f"  {name}")

        # Try to show connection status
        if name != "Unknown":
            yield Static("  [green]● Connected[/]")
        else:
            yield Static("  [dim]○ No adapter[/]")

    def update_data(self, wifi_data: dict) -> None:
        """Refresh with new WiFi data."""
        self._data = wifi_data
        self.refresh(recompose=True)
