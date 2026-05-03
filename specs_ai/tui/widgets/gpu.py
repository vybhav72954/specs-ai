"""GPU panel — name, VRAM, type badge."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from specs_ai.tui.util import fmt


class GPUPanel(Widget):
    """Displays GPU specs with Dedicated/Integrated badge."""

    DEFAULT_CSS = """
    GPUPanel { height: auto; }
    """

    def __init__(self, gpu_data: dict | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data = gpu_data or {}

    def compose(self) -> ComposeResult:
        """Build the GPU info display."""
        d = self._data
        name = d.get("name", "Unknown")
        vram = fmt(d.get("vram_gb", "?"))
        gpu_type = d.get("gpu_type", "Unknown")

        if gpu_type == "Dedicated":
            badge = "[b green]⬢ Dedicated[/]"
        elif gpu_type == "Integrated":
            badge = "[dim]⬡ Integrated[/]"
        else:
            badge = "[dim]Unknown[/]"

        yield Static("[b cyan]◈ GPU[/]")
        yield Static(f"  {name}")
        yield Static(f"  {vram} GB VRAM  {badge}")

    def update_data(self, gpu_data: dict) -> None:
        """Refresh with new GPU data."""
        self._data = gpu_data
        self.refresh(recompose=True)
