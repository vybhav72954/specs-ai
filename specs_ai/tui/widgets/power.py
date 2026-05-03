"""Power panel — battery health gauge or desktop PSU note."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from specs_ai.tui.util import fmt, usage_bar


class PowerPanel(Widget):
    """Displays battery health or desktop PSU callout."""

    DEFAULT_CSS = """
    PowerPanel { height: auto; }
    """

    def __init__(self, power_data: dict | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data = power_data or {}

    def compose(self) -> ComposeResult:
        """Build the power info display."""
        d = self._data
        has_battery = bool(d.get("has_battery", False))

        yield Static("[b cyan]⏻ POWER[/]")

        if not has_battery:
            yield Static("  [dim]Desktop — no battery detected[/]")
            yield Static("  [dim]⏚ PSU powered[/]")
            return

        bat_name = d.get("battery_name", "Unknown")
        health = d.get("health_pct", "Unknown")
        design = d.get("design_capacity_mwh", "Unknown")
        current = d.get("full_charge_capacity_mwh", "Unknown")

        yield Static(f"  {bat_name}")

        if isinstance(health, int):
            bar = usage_bar(health)
            if health > 70:
                color = "green"
            elif health > 40:
                color = "yellow"
            else:
                color = "red"
            yield Static(f"  Health: [{color}]{bar}[/]")
        else:
            yield Static("  Health: [dim]Unknown[/]")

        if design != "Unknown" and current != "Unknown":
            yield Static(f"  {fmt(design)} mWh → {fmt(current)} mWh")

    def update_data(self, power_data: dict) -> None:
        """Refresh with new power data."""
        self._data = power_data
        self.refresh(recompose=True)
