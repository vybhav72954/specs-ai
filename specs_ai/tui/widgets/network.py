"""Network panel — WiFi adapter name and connection status."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class NetworkPanel(Widget):
    """Displays WiFi adapter information."""

    DEFAULT_CSS = """
    NetworkPanel {
        height: 100%;
        border: round #00802080;
        background: #111111;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Build the network info display."""
        yield Static("[b cyan]⚡ NETWORK[/]")
        yield Static("[dim]Scanning...[/]", id="net-name")
        yield Static("", id="net-status")

    def update_data(self, data: dict) -> None:
        """Populate the panel with WiFi data."""
        name = data.get("name", "Unknown")

        try:
            self.query_one("#net-name", Static).update(f"  {name}")
            if name and name != "Unknown":
                self.query_one("#net-status", Static).update("  [green]● Connected[/]")
            else:
                self.query_one("#net-status", Static).update("  [dim]○ No adapter[/]")
        except Exception:
            pass
