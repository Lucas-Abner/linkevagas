"""
LinkeVagas GUI — Main Application Window.

Assembles all components into a two-column layout and wires up the
ProcessManager to drive the pipeline view and log viewer.
"""

from __future__ import annotations

try:
    import tkinter as tk
except ImportError as e:
    if 'tkinter' in str(e):
        import sys
        sys.stderr.write("Erro: Módulo 'tkinter' não encontrado.\n")
        sys.stderr.write("Instale-o executando: sudo apt-get install python3-tk\n")
        sys.exit(1)
    else:
        raise e

from tkinter import ttk
from pathlib import Path

from gui.theme import (
    ACCENT_BLUE, BG_CARD, BG_DARK, BORDER, FONT_HEADING,
    FONT_SMALL, TEXT_MUTED, TEXT_PRIMARY, configure_ttk_styles,
)
from gui.process_manager import AgentProcess
from gui.components.config_panel import ConfigPanel
from gui.components.control_panel import ControlPanel
from gui.components.pipeline_view import PipelineView
from gui.components.log_viewer import LogViewer
from gui.components.session_panel import SessionPanel

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class App:
    """Top-level application window."""

    def __init__(self) -> None:
        # ── window setup ────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title("LinkeVagas — Automação Inteligente de Candidaturas")
        self.root.geometry("1200x780")
        self.root.minsize(1000, 650)
        self.root.configure(bg=BG_DARK)

        configure_ttk_styles(self.root)

        # ── process manager ─────────────────────────────────────────────
        self._agent = AgentProcess(
            project_root=PROJECT_ROOT,
            on_output=self._on_output,
            on_stage=self._on_stage,
            on_complete=self._on_complete,
            on_error=self._on_error,
        )

        self._current_stage = -1

        # ── build UI ────────────────────────────────────────────────────
        self._build()

    # ── layout ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Title bar
        title_bar = tk.Frame(self.root, bg=BG_DARK)
        title_bar.pack(fill="x", padx=24, pady=(18, 6))

        tk.Label(
            title_bar,
            text="🚀  LinkeVagas",
            font=FONT_HEADING,
            fg=ACCENT_BLUE,
            bg=BG_DARK,
        ).pack(side="left")

        tk.Label(
            title_bar,
            text="Automação Inteligente de Candidaturas no LinkedIn",
            font=FONT_SMALL,
            fg=TEXT_MUTED,
            bg=BG_DARK,
        ).pack(side="left", padx=(12, 0), pady=(4, 0))

        # Separator
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(6, 0))

        # Main content: two columns
        content = tk.Frame(self.root, bg=BG_DARK)
        content.pack(fill="both", expand=True, padx=16, pady=12)

        # Left column (config + session)
        left = tk.Frame(content, bg=BG_DARK, width=420)
        left.pack(side="left", fill="both", padx=(0, 8))
        left.pack_propagate(False)

        self.config_panel = ConfigPanel(left)
        self.config_panel.pack(fill="both", expand=True, pady=(0, 8))

        self.session_panel = SessionPanel(left)
        self.session_panel.pack(fill="x")

        # Vertical separator
        tk.Frame(content, bg=BORDER, width=1).pack(side="left", fill="y", padx=4)

        # Right column (control → pipeline → log)
        right = tk.Frame(content, bg=BG_DARK)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self.control_panel = ControlPanel(
            right,
            on_start=self._handle_start,
            on_stop=self._handle_stop,
        )
        self.control_panel.pack(fill="x", pady=(0, 8))

        self.pipeline_view = PipelineView(right)
        self.pipeline_view.pack(fill="x", pady=(0, 8))

        self.log_viewer = LogViewer(right)
        self.log_viewer.pack(fill="both", expand=True)

    # ── process callbacks ───────────────────────────────────────────────

    def _handle_start(self) -> None:
        self.pipeline_view.reset()
        self.log_viewer.clear()
        self._current_stage = -1
        self._agent.start()

    def _handle_stop(self) -> None:
        self._agent.stop()

    # Thread-safe wrappers (schedule on main thread via `after`).

    def _on_output(self, line: str) -> None:
        self.root.after(0, self.log_viewer.append_line, line)

    def _on_stage(self, stage_index: int) -> None:
        self._current_stage = stage_index
        self.root.after(0, self.pipeline_view.set_stage_active, stage_index)

    def _on_complete(self) -> None:
        self.root.after(0, self.pipeline_view.mark_all_completed)
        self.root.after(0, self.control_panel.set_status, "completed")
        self.root.after(0, self.log_viewer.append_line,
                        "\n✅ Pipeline concluído com sucesso!")

    def _on_error(self, returncode: int) -> None:
        self.root.after(0, self.pipeline_view.mark_error, None)
        self.root.after(0, self.control_panel.set_status, "error")
        self.root.after(0, self.log_viewer.append_line,
                        f"\n❌ Processo encerrado com código {returncode}")

    # ── run ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the tkinter main loop."""
        self.root.mainloop()
