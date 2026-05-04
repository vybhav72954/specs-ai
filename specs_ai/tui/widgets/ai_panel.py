"""AI Recommendations panel — LLM response rendered as Rich Markdown."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Markdown, Static


class AIPanel(Widget):
    """Displays LLM upgrade recommendations with a loading state.

    The LLM response is rendered via Textual's ``Markdown`` widget so that
    tables, headers, bold/italic, and code blocks are formatted correctly
    instead of appearing as raw text.
    """

    DEFAULT_CSS = """
    AIPanel { height: auto; min-height: 4; }
    AIPanel Markdown {
        margin: 0 1;
        background: transparent;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._loading = False

    def compose(self) -> ComposeResult:
        """Build the AI panel display."""
        yield Static("[b cyan]🤖 AI UPGRADE RECOMMENDATIONS[/]", id="ai-panel-title")
        yield Static("[dim]Waiting for hardware scan...[/]", id="ai-loading")
        yield Markdown("", id="ai-markdown")

    def on_mount(self) -> None:
        """Hide the markdown widget until we have content."""
        try:
            self.query_one("#ai-markdown", Markdown).display = False
        except Exception:
            pass

    def set_loading(self, model_name: str = "gemini-2.5-flash") -> None:
        """Show the loading state, naming the model actually being queried."""
        self._loading = True
        try:
            loading = self.query_one("#ai-loading", Static)
            loading.update(f"[yellow]▌ Querying {model_name}...  ████░░░░░░░░[/]")
            loading.display = True
            self.query_one("#ai-markdown", Markdown).display = False
        except Exception:
            pass

    def set_result(self, markdown_text: str) -> None:
        """Display the LLM response as rendered Markdown."""
        self._loading = False
        try:
            self.query_one("#ai-loading", Static).display = False
            md_widget = self.query_one("#ai-markdown", Markdown)
            md_widget.update(markdown_text)
            md_widget.display = True
        except Exception:
            pass

    def set_error(self, error_msg: str) -> None:
        """Display an error message."""
        self._loading = False
        try:
            loading = self.query_one("#ai-loading", Static)
            loading.update(f"[bold red]✖ Error:[/] {error_msg}")
            loading.display = True
            self.query_one("#ai-markdown", Markdown).display = False
        except Exception:
            pass
