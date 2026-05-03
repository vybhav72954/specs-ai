"""Event log panel — timestamped scrolling activity feed."""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

MAX_LOG_LINES = 100

# Icons
ICON_START = "▶"
ICON_OK = "✔"
ICON_ERROR = "✖"
ICON_WARN = "⚠"


class EventLog(Widget):
    """Scrollable, timestamped event log with icons."""

    DEFAULT_CSS = """
    EventLog { height: auto; min-height: 3; overflow-y: auto; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._lines: list[str] = []

    def compose(self) -> ComposeResult:
        """Build the event log display."""
        yield Static("[b cyan]📋 EVENT LOG[/]", id="log-title")
        yield Static("", id="log-content")

    def log(self, message: str, icon: str = ICON_START) -> None:
        """Add a timestamped line to the log."""
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"  [{ts}] {icon} {message}"
        self._lines.append(line)
        if len(self._lines) > MAX_LOG_LINES:
            self._lines = self._lines[-MAX_LOG_LINES:]
        self._refresh_display()

    def log_ok(self, message: str) -> None:
        """Log a success message."""
        self.log(message, f"[green]{ICON_OK}[/]")

    def log_error(self, message: str) -> None:
        """Log an error message."""
        self.log(message, f"[red]{ICON_ERROR}[/]")

    def log_warn(self, message: str) -> None:
        """Log a warning message."""
        self.log(message, f"[yellow]{ICON_WARN}[/]")

    def log_start(self, message: str) -> None:
        """Log a started/in-progress message."""
        self.log(message, f"[cyan]{ICON_START}[/]")

    def _refresh_display(self) -> None:
        """Update the displayed log content."""
        try:
            content = self.query_one("#log-content", Static)
            content.update("\n".join(self._lines[-8:]))  # Show last 8 lines
        except Exception:
            pass
