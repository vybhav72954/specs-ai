"""Power panel — battery health gauge or desktop PSU note."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from specs_ai.tui.util import usage_bar


class PowerPanel(Widget):
    """Displays battery health or desktop PSU callout."""

    DEFAULT_CSS = """
    PowerPanel {
        height: 100%;
        overflow-y: auto;
        border: round #00802080;
        background: #111111;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Build the power info display."""
        yield Static("[b cyan]⏻ POWER[/]")
        yield Static("[dim]Scanning...[/]", id="power-content")

    def update_data(self, data: dict) -> None:
        """Populate the panel with power data."""
        has_battery = bool(data.get("has_battery", False))

        if not has_battery:
            try:
                self.query_one("#power-content", Static).update(
                    "  [dim]Desktop — no battery detected[/]\n"
                    "  [dim]⏚ PSU powered[/]"
                )
            except Exception:
                pass
            return

        bat_name = data.get("battery_name", "Unknown")
        health = data.get("health_pct", "Unknown")
        design = data.get("design_capacity_mwh", "Unknown")
        current = data.get("full_charge_capacity_mwh", "Unknown")

        lines: list[str] = [f"  {bat_name}"]

        if isinstance(health, (int, float)):
            health_val = int(health)
            bar = usage_bar(health_val)
            if health_val > 70:
                lines.append(f"  Health: [green]{bar}[/]")
            elif health_val > 40:
                lines.append(f"  Health: [yellow]{bar}[/]")
            else:
                lines.append(f"  Health: [red]{bar}[/]")
        else:
            lines.append("  Health: [dim]Unknown[/]")

        if design != "Unknown" and current != "Unknown":
            d_fmt = int(design) if isinstance(design, float) and design == int(design) else design
            c_fmt = int(current) if isinstance(current, float) and current == int(current) else current
            lines.append(f"  {d_fmt} mWh → {c_fmt} mWh")

        try:
            self.query_one("#power-content", Static).update("\n".join(lines))
        except Exception:
            pass
