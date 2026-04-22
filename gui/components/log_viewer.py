"""
LinkeVagas GUI — Log Viewer.

Real-time terminal widget that displays stdout/stderr from the agent subprocess
with colour-coded lines and auto-scroll.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from gui.theme import (
    ACCENT_BLUE, BG_CARD, BG_DARK, BG_INPUT, BORDER, ERROR_RED,
    FONT_BODY, FONT_BUTTON, FONT_MONO, FONT_SMALL, FONT_SUBHEADING,
    MUTED_GRAY, SUCCESS_GREEN, TEXT_MUTED, TEXT_PRIMARY, WARNING_AMBER,
)

MAX_LINES = 5000


class LogViewer(ttk.Frame):
    """Scrollable, colour-coded log terminal."""

    def __init__(self, parent: tk.Widget, **kw) -> None:
        super().__init__(parent, style="Card.TFrame", **kw)
        self._build()

    def _build(self) -> None:
        outer = tk.Frame(self, bg=BG_CARD)
        outer.pack(fill="both", expand=True, padx=16, pady=12)

        # Header row
        header = tk.Frame(outer, bg=BG_CARD)
        header.pack(fill="x", pady=(0, 8))
        tk.Label(header, text="📋  Terminal / Log", font=FONT_SUBHEADING,
                 fg=ACCENT_BLUE, bg=BG_CARD).pack(side="left")
        tk.Button(header, text="🗑 Limpar", font=FONT_SMALL, bg=BG_CARD,
                  fg=TEXT_MUTED, relief="flat", cursor="hand2",
                  command=self.clear).pack(side="right")

        # Text area + scrollbar
        text_frame = tk.Frame(outer, bg=BG_INPUT)
        text_frame.pack(fill="both", expand=True)

        self._scrollbar = tk.Scrollbar(text_frame, orient="vertical",
                                       bg=BORDER, troughcolor=BG_INPUT)
        self._scrollbar.pack(side="right", fill="y")

        self._text = tk.Text(
            text_frame,
            wrap="word",
            font=FONT_MONO,
            bg="#0d0f17",
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            selectbackground=ACCENT_BLUE,
            relief="flat",
            bd=8,
            state="disabled",
            yscrollcommand=self._scrollbar.set,
        )
        self._text.pack(fill="both", expand=True)
        self._scrollbar.config(command=self._text.yview)

        # Colour tags
        self._text.tag_configure("success", foreground=SUCCESS_GREEN)
        self._text.tag_configure("warning", foreground=WARNING_AMBER)
        self._text.tag_configure("error",   foreground=ERROR_RED)
        self._text.tag_configure("info",    foreground=ACCENT_BLUE)
        self._text.tag_configure("muted",   foreground=MUTED_GRAY)

    # ── public API ──────────────────────────────────────────────────────

    def append_line(self, line: str) -> None:
        """Append a line to the log (thread-safe via ``after``)."""
        self._text.after(0, self._insert, line)

    def clear(self) -> None:
        """Clear all log content."""
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        self._text.config(state="disabled")

    # ── internal ────────────────────────────────────────────────────────

    def _insert(self, line: str) -> None:
        self._text.config(state="normal")

        tag = self._detect_tag(line)
        self._text.insert("end", line + "\n", tag)

        # Limit total lines.
        total = int(self._text.index("end-1c").split(".")[0])
        if total > MAX_LINES:
            self._text.delete("1.0", f"{total - MAX_LINES}.0")

        self._text.see("end")
        self._text.config(state="disabled")

    @staticmethod
    def _detect_tag(line: str) -> str:
        if "✅" in line or "sucesso" in line.lower():
            return "success"
        if "⚠️" in line or "⚠" in line:
            return "warning"
        if "❌" in line or "Erro" in line or "ERROR" in line:
            return "error"
        if "🔍" in line or "DEBUG" in line:
            return "info"
        if line.startswith("═") or line.startswith("─"):
            return "muted"
        return ""
