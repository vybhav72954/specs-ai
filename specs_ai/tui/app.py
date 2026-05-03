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

    def __init__(self, model: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._specs: dict | None = None
        self._verbose = False
        self._help_visible = False
        # Monotonic counter used to invalidate stale worker output when
        # the user kicks off a new scan / re-query before the previous one
        # has finished. Thread workers cannot be force-cancelled in Python,
        # so we cooperatively drop UI updates whose token is out of date.
        self._scan_token = 0
        self._model = model

    def compose(self) -> ComposeResult:
        """Build the full dashboard layout."""
        with Horizontal(id="outer-grid"):
            yield MatrixRain(columns=2, id="rain-left")

            with Vertical(id="main-content"):
                yield HeaderWidget(initial_uptime=0, id="header")

                # Hardware panel grid — panels placed directly, CSS grid handles layout
                with Vertical(id="panel-grid"):
                    yield SystemPanel(id="sys-panel")
                    yield CPUPanel(id="cpu-panel")
                    yield GPUPanel(id="gpu-panel")
                    yield RAMPanel(id="ram-panel")
                    yield StoragePanel(id="storage-panel")
                    yield NetworkPanel(id="net-panel")
                    yield MoboPanel(id="mobo-panel")
                    yield PowerPanel(id="power-panel")
                    # 9th cell is empty (only 8 panels in a 3x3 grid)

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
        self._scan_token += 1
        token = self._scan_token
        self._ui_log("start", "Hardware extraction started...")
        # exclusive=True cancels any prior worker in this group; the token
        # check below catches the case where Python can't actually kill the
        # already-running thread.
        self.run_worker(
            lambda: self._collect_and_display(token),
            thread=True,
            exclusive=True,
            group="scan",
        )

    def _is_current(self, token: int) -> bool:
        """Return True if `token` matches the latest scan token."""
        return token == self._scan_token

    # ── Main-thread helpers (callable via call_from_thread) ──────────
    # All DOM access lives here so worker threads never touch the
    # widget tree directly.

    def _ui_log(self, kind: str, msg: str) -> None:
        """Main-thread: append a line to the event log."""
        log = self.query_one("#event-log", EventLog)
        {
            "start": log.log_start,
            "ok": log.log_ok,
            "error": log.log_error,
            "warn": log.log_warn,
        }[kind](msg)

    def _ui_ai_loading(self) -> None:
        """Main-thread: switch the AI panel to its loading state."""
        model_name = self._model or "gemini-2.5-flash"
        self.query_one("#ai-panel", AIPanel).set_loading(model_name)

    def _ui_ai_result(self, text: str) -> None:
        """Main-thread: render an LLM result in the AI panel."""
        self.query_one("#ai-panel", AIPanel).set_result(text)

    def _ui_ai_error(self, msg: str) -> None:
        """Main-thread: render an error in the AI panel."""
        self.query_one("#ai-panel", AIPanel).set_error(msg)

    def _ui_set_uptime(self, seconds: int) -> None:
        """Main-thread: push a real uptime value into the header."""
        self.query_one("#header", HeaderWidget).uptime_seconds = seconds

    # ── Workers (thread=True; never touch widgets directly) ──────────

    def _collect_and_display(self, token: int) -> None:
        """Background worker: collect specs and query LLM."""
        import pythoncom

        from specs_ai.extractor import collect

        # WMI uses COM, which must be initialized per-thread on Windows.
        pythoncom.CoInitialize()
        try:
            # ── Phase 1: Collect hardware specs ──
            try:
                specs = collect()
                if not self._is_current(token):
                    return
                self._specs = dataclasses.asdict(specs)
                self.call_from_thread(self._ui_log, "ok", "Hardware specs collected")
            except Exception as e:
                if self._is_current(token):
                    self.call_from_thread(self._ui_log, "error", f"Extraction failed: {e}")
                return
        finally:
            pythoncom.CoUninitialize()

        # ── Phase 2: Populate panels ──
        if not self._is_current(token):
            return
        self.call_from_thread(self._populate_panels)

        # ── Phase 3: Set uptime on header ──
        uptime = self._specs.get("system", {}).get("uptime_seconds", 0)
        if isinstance(uptime, int) and self._is_current(token):
            self.call_from_thread(self._ui_set_uptime, uptime)

        # ── Phase 4: Query LLM ──
        if not self._is_current(token):
            return
        self.call_from_thread(self._ui_ai_loading)
        self.call_from_thread(self._ui_log, "start", "Querying Gemini API...")

        try:
            from specs_ai.llm_agent import get_recommendations
            kwargs = {"verbose": self._verbose}
            if self._model:
                kwargs["model"] = self._model
            result = get_recommendations(self._specs, **kwargs)
            if not self._is_current(token):
                return
            self.call_from_thread(self._ui_ai_result, result)
            self.call_from_thread(self._ui_log, "ok", "Recommendations received")
        except EnvironmentError as e:
            if self._is_current(token):
                self.call_from_thread(self._ui_ai_error, str(e))
                self.call_from_thread(self._ui_log, "error", f"API key error: {e}")
        except RuntimeError as e:
            if self._is_current(token):
                self.call_from_thread(self._ui_ai_error, str(e))
                self.call_from_thread(self._ui_log, "error", f"API error: {e}")

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
        self._ui_log("start", "Re-scanning hardware...")
        self._run_scan()

    def action_toggle_explain(self) -> None:
        """Toggle between compact and verbose LLM output."""
        self._verbose = not self._verbose
        mode = "detailed" if self._verbose else "compact"
        self._ui_log("start", f"Switched to {mode} mode, re-querying...")

        if self._specs:
            self._scan_token += 1
            token = self._scan_token
            self._ui_ai_loading()
            self.run_worker(
                lambda: self._requery_llm(token),
                thread=True,
                exclusive=True,
                group="scan",
            )

    def _requery_llm(self, token: int) -> None:
        """Background worker: re-query LLM with current specs."""
        try:
            from specs_ai.llm_agent import get_recommendations
            kwargs = {"verbose": self._verbose}
            if self._model:
                kwargs["model"] = self._model
            result = get_recommendations(self._specs, **kwargs)
            if not self._is_current(token):
                return
            self.call_from_thread(self._ui_ai_result, result)
            self.call_from_thread(self._ui_log, "ok", "Recommendations updated")
        except Exception as e:
            if self._is_current(token):
                self.call_from_thread(self._ui_ai_error, str(e))
                self.call_from_thread(self._ui_log, "error", f"Re-query failed: {e}")

    def action_export(self) -> None:
        """Export specs to specs_report.json in the current directory."""
        if not self._specs:
            self._ui_log("warn", "No specs available to export")
            return

        path = Path.cwd() / "specs_report.json"
        try:
            path.write_text(json.dumps(self._specs, indent=2, default=str))
            self._ui_log("ok", f"Specs exported to {path.name}")
        except Exception as e:
            self._ui_log("error", f"Export failed: {e}")

    def action_toggle_help(self) -> None:
        """Show or hide the help overlay."""
        overlay = self.query_one("#help-overlay", Static)
        self._help_visible = not self._help_visible
        if self._help_visible:
            overlay.add_class("visible")
        else:
            overlay.remove_class("visible")
