"""Motherboard panel — manufacturer, model, system model."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class MoboPanel(Widget):
    """Displays motherboard information."""

    DEFAULT_CSS = """
    MoboPanel { height: auto; }
    """

    def __init__(self, mobo_data: dict | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data = mobo_data or {}

    def compose(self) -> ComposeResult:
        """Build the motherboard info display."""
        d = self._data
        mfr = d.get("manufacturer", "Unknown")
        model = d.get("model", "Unknown")
        sys_model = d.get("system_model", "Unknown")

        yield Static("[b cyan]⊟ MOTHERBOARD[/]")
        yield Static(f"  {mfr}")
        yield Static(f"  {model}")
        if sys_model and sys_model != "Unknown":
            yield Static(f"  [dim][{sys_model}][/]")

    def update_data(self, mobo_data: dict) -> None:
        """Refresh with new motherboard data."""
        self._data = mobo_data
        self.refresh(recompose=True)
