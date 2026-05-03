"""Event log panel — timestamped scrolling activity feed."""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog, Static

MAX_LOG_LINES = 100

# Icons
ICON_START = "▶"
ICON_OK = "✔"
ICON_ERROR = "✖"
ICON_WARN = "⚠"


class EventLog(Widget):
    """Scrollable, timestamped event log with icons.

    Backed by Textual's RichLog so the full MAX_LOG_LINES buffer is
    actually accessible — the user can scroll up to inspect older entries
    rather than only seeing whatever fits in the panel's visible height.
    """

    DEFAULT_CSS = """
    EventLog { height: auto; min-height: 3; }
    EventLog > RichLog { height: 1fr; background: #111111; }
    """

    def compose(self) -> ComposeResult:
        """Build the event log display."""
        yield Static("[b cyan]📋 EVENT LOG[/]", id="log-title")
        yield RichLog(
            id="log-content",
            max_lines=MAX_LOG_LINES,
            markup=True,
            auto_scroll=True,
            wrap=False,
        )

    def log(self, message: str, icon: str = ICON_START) -> None:
        """Add a timestamped line to the log."""
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"  \\[{ts}] {icon} {message}"
        try:
            self.query_one("#log-content", RichLog).write(line)
        except Exception:
            pass

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
