"""Motherboard panel — manufacturer, model, system model."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class MoboPanel(Widget):
    """Displays motherboard information."""

    DEFAULT_CSS = """
    MoboPanel {
        height: auto;
        border: round #00802080;
        background: #111111;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Build the motherboard info display."""
        yield Static("[b cyan]⊟ MOTHERBOARD[/]")
        yield Static("[dim]Scanning...[/]", id="mobo-content")

    def update_data(self, data: dict) -> None:
        """Populate the panel with motherboard data."""
        mfr = data.get("manufacturer", "Unknown")
        model = data.get("model", "Unknown")
        sys_model = data.get("system_model", "Unknown")

        lines = [f"  {mfr}", f"  {model}"]
        if sys_model and sys_model != "Unknown":
            lines.append(f"  [dim][{sys_model}][/]")

        try:
            self.query_one("#mobo-content", Static).update("\n".join(lines))
        except Exception:
            pass
