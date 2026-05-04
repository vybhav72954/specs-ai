"""GPU panel — name, VRAM, type badge."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class GPUPanel(Widget):
    """Displays GPU specs with Dedicated/Integrated badge."""

    DEFAULT_CSS = """
    GPUPanel {
        height: 100%;
        overflow-y: auto;
        border: round #00802080;
        background: #111111;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Build the GPU info display."""
        yield Static("[b cyan]◈ GPU[/]")
        yield Static("[dim]Scanning...[/]", id="gpu-name")
        yield Static("", id="gpu-vram")

    def update_data(self, data: dict) -> None:
        """Populate the panel with GPU data."""
        name = data.get("name", "Unknown")
        vram = data.get("vram_gb", "?")
        gpu_type = data.get("gpu_type", "Unknown")

        # Format VRAM — drop .0
        if isinstance(vram, float) and vram == int(vram):
            vram = int(vram)

        if gpu_type == "Dedicated":
            badge = "[b green]⬢ Dedicated[/]"
        elif gpu_type == "Integrated":
            badge = "[dim]⬡ Integrated[/]"
        else:
            badge = "[dim]Unknown[/]"

        try:
            self.query_one("#gpu-name", Static).update(f"  {name}")
            self.query_one("#gpu-vram", Static).update(f"  {vram} GB VRAM  {badge}")
        except Exception:
            pass
