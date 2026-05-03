"""AI Recommendations panel — LLM response with loading animation."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class AIPanel(Widget):
    """Displays LLM upgrade recommendations with a loading state."""

    DEFAULT_CSS = """
    AIPanel { height: auto; min-height: 4; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._content = "[dim]Waiting for hardware scan...[/]"
        self._loading = False

    def compose(self) -> ComposeResult:
        """Build the AI panel display."""
        yield Static("[b cyan]🤖 AI UPGRADE RECOMMENDATIONS[/]", id="ai-panel-title")
        yield Static(self._content, id="ai-content")

    def set_loading(self, model_name: str = "gemini-2.5-flash") -> None:
        """Show the loading state, naming the model actually being queried."""
        self._loading = True
        self._content = f"[yellow]▌ Querying {model_name}...  ████░░░░░░░░[/]"
        try:
            self.query_one("#ai-content", Static).update(self._content)
        except Exception:
            pass

    def set_result(self, markdown_text: str) -> None:
        """Display the LLM response."""
        self._loading = False
        self._content = markdown_text
        try:
            self.query_one("#ai-content", Static).update(self._content)
        except Exception:
            pass

    def set_error(self, error_msg: str) -> None:
        """Display an error message."""
        self._loading = False
        self._content = f"[bold red]✖ Error:[/] {error_msg}"
        try:
            self.query_one("#ai-content", Static).update(self._content)
        except Exception:
            pass
