"""System panel — OS name, build, type, install date, uptime."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from specs_ai.tui.util import UPTIME_CRIT_SECS, UPTIME_WARN_SECS


class SystemPanel(Widget):
    """Displays OS and machine-type metadata."""

    DEFAULT_CSS = """
    SystemPanel { height: auto; }
    """

    def __init__(self, system_data: dict | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data = system_data or {}

    def compose(self) -> ComposeResult:
        """Build the system info display."""
        d = self._data
        os_name = d.get("os_name", "Unknown")
        os_build = d.get("os_build", "Unknown")
        sys_type = d.get("system_type", "Unknown")
        install = d.get("os_install_date", "Unknown")
        uptime = d.get("uptime_seconds", "Unknown")

        yield Static("[b cyan]⊞ SYSTEM[/]")
        yield Static(f"  {os_name}")
        yield Static(f"  Build {os_build}")
        yield Static(f"  {sys_type}  │  Installed: {install}")

        if isinstance(uptime, int):
            days = uptime // 86400
            hours = (uptime % 86400) // 3600
            mins = (uptime % 3600) // 60
            up_str = f"{days}d {hours}h {mins}m"
            if uptime >= UPTIME_CRIT_SECS:
                yield Static(f"  Uptime: [bold red]{up_str}[/]")
            elif uptime >= UPTIME_WARN_SECS:
                yield Static(f"  Uptime: [bold yellow]{up_str}[/]")
            else:
                yield Static(f"  Uptime: [green]{up_str}[/]")

    def update_data(self, system_data: dict) -> None:
        """Refresh the panel with new data."""
        self._data = system_data
        self.refresh(recompose=True)
