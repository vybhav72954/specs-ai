"""specs-ai TUI — Hacker-esque Hardware Dashboard."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from specs_ai.tui.widgets.header import HeaderWidget
from specs_ai.tui.widgets.matrix_rain import MatrixRain
from specs_ai.tui.widgets.system import SystemPanel
from specs_ai.tui.widgets.cpu import CPUPanel
from specs_ai.tui.widgets.ram import RAMPanel
from specs_ai.tui.widgets.gpu import GPUPanel
from specs_ai.tui.widgets.storage import StoragePanel
from specs_ai.tui.widgets.network import NetworkPanel
from specs_ai.tui.widgets.power import PowerPanel
from specs_ai.tui.widgets.mobo import MoboPanel
from specs_ai.tui.widgets.ai_panel import AIPanel
from specs_ai.tui.widgets.logs import EventLog


class SpecsAIApp(App):
    """The main specs-ai TUI application."""

    TITLE = "SPECS-AI"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "rescan", "Re-scan"),
        Binding("e", "toggle_explain", "Explain"),
        Binding("s", "export", "Export"),
        Binding("question_mark", "toggle_help", "Help"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._specs: dict | None = None
        self._verbose = False
        self._help_visible = False

    def compose(self) -> ComposeResult:
        """Build the full dashboard layout."""
        with Horizontal(id="outer-grid"):
            yield MatrixRain(columns=2, id="rain-left")

            with Vertical(id="main-content"):
                yield HeaderWidget(initial_uptime=0, id="header")

                # Hardware panel grid: 3 columns x 3 rows
                with Vertical(id="panel-grid"):
                    # Row 1: System | CPU | GPU
                    with Horizontal():
                        yield SystemPanel(classes="hw-panel", id="sys-panel")
                        yield CPUPanel(classes="hw-panel", id="cpu-panel")
                        yield GPUPanel(classes="hw-panel", id="gpu-panel")

                    # Row 2: RAM | Storage | Network
                    with Horizontal():
                        yield RAMPanel(classes="hw-panel", id="ram-panel")
                        yield StoragePanel(classes="hw-panel", id="storage-panel")
                        yield NetworkPanel(classes="hw-panel", id="net-panel")

                    # Row 3: Motherboard | Power (spans 2 cols via width)
                    with Horizontal():
                        yield MoboPanel(classes="hw-panel", id="mobo-panel")
                        yield PowerPanel(classes="hw-panel", id="power-panel")

                # AI Recommendations (full-width)
                with Vertical(id="bottom-section"):
                    yield AIPanel(id="ai-panel")
                    yield EventLog(id="event-log")

                # Footer keybinds
                yield Static(
                    " [b cyan][Q][/] Quit  "
                    "[b cyan][R][/] Re-scan  "
                    "[b cyan][E][/] Explain  "
                    "[b cyan][S][/] Export  "
                    "[b cyan][?][/] Help",
                    id="footer-bar",
                )

                # Help overlay (hidden by default)
                yield Static(
                    "[b cyan]⌨ KEYBINDINGS[/]\n"
                    "  [b]Q[/] / Ctrl+C — Quit the dashboard\n"
                    "  [b]R[/] — Re-scan hardware and re-query the LLM\n"
                    "  [b]E[/] — Toggle compact table / detailed --explain mode\n"
                    "  [b]S[/] — Export full specs to specs_report.json\n"
                    "  [b]?[/] — Toggle this help overlay",
                    id="help-overlay",
                )

            yield MatrixRain(columns=2, id="rain-right")

    def on_mount(self) -> None:
        """Start the initial hardware scan."""
        self._run_scan()

    def _run_scan(self) -> None:
        """Run hardware collection in a background worker."""
        log = self.query_one("#event-log", EventLog)
        log.log_start("Hardware extraction started...")
        self.run_worker(self._collect_and_display, thread=True)

    def _collect_and_display(self) -> None:
        """Background worker: collect specs and query LLM."""
        from specs_ai.extractor import collect

        log = self.query_one("#event-log", EventLog)
        ai = self.query_one("#ai-panel", AIPanel)

        # ── Phase 1: Collect hardware specs ──
        try:
            specs = collect()
            self._specs = dataclasses.asdict(specs)
            self.call_from_thread(log.log_ok, "Hardware specs collected")
        except Exception as e:
            self.call_from_thread(log.log_error, f"Extraction failed: {e}")
            return

        # ── Phase 2: Populate panels ──
        self.call_from_thread(self._populate_panels)

        # ── Phase 3: Set uptime on header ──
        uptime = self._specs.get("system", {}).get("uptime_seconds", 0)
        if isinstance(uptime, int):
            header = self.query_one("#header", HeaderWidget)
            self.call_from_thread(setattr, header, "uptime_seconds", uptime)

        # ── Phase 4: Query LLM ──
        self.call_from_thread(ai.set_loading)
        self.call_from_thread(log.log_start, "Querying Gemini API...")

        try:
            from specs_ai.llm_agent import get_recommendations
            result = get_recommendations(self._specs, verbose=self._verbose)
            self.call_from_thread(ai.set_result, result)
            self.call_from_thread(log.log_ok, "Recommendations received")
        except EnvironmentError as e:
            self.call_from_thread(ai.set_error, str(e))
            self.call_from_thread(log.log_error, f"API key error: {e}")
        except RuntimeError as e:
            self.call_from_thread(ai.set_error, str(e))
            self.call_from_thread(log.log_error, f"API error: {e}")

    def _populate_panels(self) -> None:
        """Push collected data into all hardware panels."""
        if not self._specs:
            return

        self.query_one("#sys-panel", SystemPanel).update_data(
            self._specs.get("system", {})
        )
        self.query_one("#cpu-panel", CPUPanel).update_data(
            self._specs.get("cpu", {})
        )
        self.query_one("#gpu-panel", GPUPanel).update_data(
            self._specs.get("gpu", {})
        )
        self.query_one("#ram-panel", RAMPanel).update_data(
            self._specs.get("ram", {})
        )
        self.query_one("#storage-panel", StoragePanel).update_data(
            self._specs.get("drives", [])
        )
        self.query_one("#net-panel", NetworkPanel).update_data(
            self._specs.get("wifi", {})
        )
        self.query_one("#mobo-panel", MoboPanel).update_data(
            self._specs.get("motherboard", {})
        )
        self.query_one("#power-panel", PowerPanel).update_data(
            self._specs.get("power", {})
        )

    # ── Keybinding actions ────────────────────────────────────

    def action_rescan(self) -> None:
        """Re-scan hardware and re-query the LLM."""
        log = self.query_one("#event-log", EventLog)
        log.log_start("Re-scanning hardware...")
        self._run_scan()

    def action_toggle_explain(self) -> None:
        """Toggle between compact and verbose LLM output."""
        self._verbose = not self._verbose
        log = self.query_one("#event-log", EventLog)
        mode = "detailed" if self._verbose else "compact"
        log.log_start(f"Switched to {mode} mode, re-querying...")

        if self._specs:
            ai = self.query_one("#ai-panel", AIPanel)
            ai.set_loading()
            self.run_worker(self._requery_llm, thread=True)

    def _requery_llm(self) -> None:
        """Background worker: re-query LLM with current specs."""
        ai = self.query_one("#ai-panel", AIPanel)
        log = self.query_one("#event-log", EventLog)

        try:
            from specs_ai.llm_agent import get_recommendations
            result = get_recommendations(self._specs, verbose=self._verbose)
            self.call_from_thread(ai.set_result, result)
            self.call_from_thread(log.log_ok, "Recommendations updated")
        except Exception as e:
            self.call_from_thread(ai.set_error, str(e))
            self.call_from_thread(log.log_error, f"Re-query failed: {e}")

    def action_export(self) -> None:
        """Export specs to specs_report.json in the current directory."""
        log = self.query_one("#event-log", EventLog)
        if not self._specs:
            log.log_warn("No specs available to export")
            return

        path = Path.cwd() / "specs_report.json"
        try:
            path.write_text(json.dumps(self._specs, indent=2, default=str))
            log.log_ok(f"Specs exported to {path.name}")
        except Exception as e:
            log.log_error(f"Export failed: {e}")

    def action_toggle_help(self) -> None:
        """Show or hide the help overlay."""
        overlay = self.query_one("#help-overlay", Static)
        self._help_visible = not self._help_visible
        if self._help_visible:
            overlay.add_class("visible")
        else:
            overlay.remove_class("visible")
