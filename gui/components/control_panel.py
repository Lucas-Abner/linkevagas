"""
LinkeVagas GUI — Control Panel.

Provides Start / Stop buttons and a visual status badge for the agent pipeline.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from gui.theme import (
    ACCENT_BLUE, BG_CARD, BG_DARK, ERROR_RED, FONT_BODY, FONT_BUTTON,
    FONT_SUBHEADING, MUTED_GRAY, SUCCESS_GREEN, TEXT_PRIMARY,
    TEXT_SECONDARY, WARNING_AMBER,
)


# Status configuration
_STATUS_CONFIG = {
    "idle":      {"text": "⏸  Ocioso",     "fg": MUTED_GRAY,    "bg": "#23263a"},
    "running":   {"text": "▶  Executando",  "fg": WARNING_AMBER, "bg": "#3a3520"},
    "completed": {"text": "✅  Concluído",  "fg": SUCCESS_GREEN, "bg": "#1a3a22"},
    "error":     {"text": "❌  Erro",       "fg": ERROR_RED,     "bg": "#3a1a1a"},
    "stopped":   {"text": "⏹  Parado",     "fg": MUTED_GRAY,    "bg": "#23263a"},
}


class ControlPanel(ttk.Frame):
    """
    Start/Stop buttons + status indicator.

    Parameters
    ----------
    on_start:
        Callback invoked when the user clicks "Iniciar Pipeline".
    on_stop:
        Callback invoked when the user clicks "Parar".
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_start: Callable[[], None] = lambda: None,
        on_stop:  Callable[[], None] = lambda: None,
        **kw,
    ) -> None:
        super().__init__(parent, style="Card.TFrame", **kw)
        self._on_start = on_start
        self._on_stop  = on_stop
        self._build()
        self.set_status("idle")

    # ── build ───────────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = tk.Frame(self, bg=BG_CARD)
        outer.pack(fill="x", padx=16, pady=12)

        # Header
        tk.Label(
            outer, text="🎮  Controle do Agente", font=FONT_SUBHEADING,
            fg=ACCENT_BLUE, bg=BG_CARD, anchor="w",
        ).pack(anchor="w", pady=(0, 10))

        # Button row
        btn_row = tk.Frame(outer, bg=BG_CARD)
        btn_row.pack(fill="x")

        self._start_btn = tk.Button(
            btn_row,
            text="▶  Iniciar Pipeline",
            font=FONT_BUTTON,
            bg=SUCCESS_GREEN,
            fg="#ffffff",
            activebackground="#3ddf80",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            padx=18, pady=10,
            command=self._handle_start,
        )
        self._start_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self._stop_btn = tk.Button(
            btn_row,
            text="⏹  Parar",
            font=FONT_BUTTON,
            bg=ERROR_RED,
            fg="#ffffff",
            activebackground="#f55a4e",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            padx=18, pady=10,
            state="disabled",
            command=self._handle_stop,
        )
        self._stop_btn.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # Status badge
        self._status_frame = tk.Frame(outer, bg="#23263a", padx=12, pady=6)
        self._status_frame.pack(fill="x", pady=(12, 0))

        self._status_label = tk.Label(
            self._status_frame,
            text="⏸  Ocioso",
            font=FONT_BODY,
            fg=MUTED_GRAY,
            bg="#23263a",
            anchor="center",
        )
        self._status_label.pack(fill="x")

    # ── actions ─────────────────────────────────────────────────────────

    def _handle_start(self) -> None:
        self.set_status("running")
        self._on_start()

    def _handle_stop(self) -> None:
        self.set_status("stopped")
        self._on_stop()

    # ── public API ──────────────────────────────────────────────────────

    def set_status(self, status: str) -> None:
        """
        Update the status badge and button states.

        Parameters
        ----------
        status : str
            One of ``"idle"``, ``"running"``, ``"completed"``, ``"error"``,
            ``"stopped"``.
        """
        cfg = _STATUS_CONFIG.get(status, _STATUS_CONFIG["idle"])
        self._status_label.config(text=cfg["text"], fg=cfg["fg"], bg=cfg["bg"])
        self._status_frame.config(bg=cfg["bg"])

        if status == "running":
            self._start_btn.config(state="disabled")
            self._stop_btn.config(state="normal")
        else:
            self._start_btn.config(state="normal")
            self._stop_btn.config(state="disabled")
