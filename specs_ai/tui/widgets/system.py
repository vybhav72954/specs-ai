"""System panel — OS name, build, type, install date, uptime."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from specs_ai.tui.util import UPTIME_CRIT_SECS, UPTIME_WARN_SECS


class SystemPanel(Widget):
    """Displays OS and machine-type metadata."""

    DEFAULT_CSS = """
    SystemPanel {
        height: auto;
        border: round #00802080;
        background: #111111;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Build the system info display."""
        yield Static("[b cyan]⊞ SYSTEM[/]")
        yield Static("[dim]Scanning...[/]", id="sys-os")
        yield Static("", id="sys-build")
        yield Static("", id="sys-type")
        yield Static("", id="sys-uptime")

    def update_data(self, data: dict) -> None:
        """Populate the panel with system data."""
        os_name = data.get("os_name", "Unknown")
        os_build = data.get("os_build", "Unknown")
        sys_type = data.get("system_type", "Unknown")
        install = data.get("os_install_date", "Unknown")
        uptime = data.get("uptime_seconds", "Unknown")

        try:
            self.query_one("#sys-os", Static).update(f"  {os_name}")
            self.query_one("#sys-build", Static).update(f"  Build {os_build}")
            self.query_one("#sys-type", Static).update(f"  {sys_type}  │  Installed: {install}")

            if isinstance(uptime, int):
                days = uptime // 86400
                hours = (uptime % 86400) // 3600
                mins = (uptime % 3600) // 60
                up_str = f"{days}d {hours}h {mins}m"
                if uptime >= UPTIME_CRIT_SECS:
                    self.query_one("#sys-uptime", Static).update(f"  Uptime: [bold red]{up_str}[/]")
                elif uptime >= UPTIME_WARN_SECS:
                    self.query_one("#sys-uptime", Static).update(f"  Uptime: [bold yellow]{up_str}[/]")
                else:
                    self.query_one("#sys-uptime", Static).update(f"  Uptime: [green]{up_str}[/]")
            else:
                self.query_one("#sys-uptime", Static).update("")
        except Exception:
            pass
