"""
LinkeVagas GUI — Pipeline Progress View.

Displays the 6 pipeline stages as a horizontal step indicator with colour-coded
status icons and connecting lines.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from gui.theme import (
    ACCENT_BLUE, BG_CARD, BORDER, ERROR_RED, FONT_SMALL,
    FONT_SUBHEADING, MUTED_GRAY, SUCCESS_GREEN, TEXT_SECONDARY, WARNING_AMBER,
)

_STAGES = [
    "Buscar\nVagas",
    "Analisar\nATS",
    "Ler\nCurrículo",
    "Otimizar\nCurrículo",
    "Converter\nPDF",
    "Enviar\nCandidatura",
]

_STATUS_ICON  = {"waiting": "⏳", "in_progress": "🔄", "completed": "✅", "error": "❌"}
_STATUS_COLOR = {"waiting": MUTED_GRAY, "in_progress": WARNING_AMBER, "completed": SUCCESS_GREEN, "error": ERROR_RED}
_STATUS_BG    = {"waiting": "#1e2030", "in_progress": "#2e2a1a", "completed": "#1a2e1f", "error": "#2e1a1a"}


class PipelineView(ttk.Frame):
    """Visual horizontal step indicator for the 6-stage pipeline."""

    def __init__(self, parent: tk.Widget, **kw) -> None:
        super().__init__(parent, style="Card.TFrame", **kw)
        self._widgets: list[dict] = []
        self._statuses = ["waiting"] * len(_STAGES)
        self._build()

    def _build(self) -> None:
        outer = tk.Frame(self, bg=BG_CARD)
        outer.pack(fill="x", padx=16, pady=12)
        tk.Label(outer, text="📊  Progresso do Pipeline", font=FONT_SUBHEADING,
                 fg=ACCENT_BLUE, bg=BG_CARD, anchor="w").pack(anchor="w", pady=(0, 12))
        row = tk.Frame(outer, bg=BG_CARD)
        row.pack(fill="x")
        for i, name in enumerate(_STAGES):
            if i > 0:
                tk.Frame(row, bg=BORDER, height=2).pack(side="left", fill="x", expand=True, pady=(0, 20))
            self._make_step(row, name)

    def _make_step(self, parent: tk.Widget, name: str) -> None:
        f = tk.Frame(parent, bg=BG_CARD)
        c = tk.Frame(f, bg="#1e2030", width=48, height=48, highlightthickness=2, highlightbackground=MUTED_GRAY)
        c.pack_propagate(False); c.pack(padx=6)
        icon = tk.Label(c, text="⏳", font=("Segoe UI", 16), bg="#1e2030", fg=MUTED_GRAY, anchor="center")
        icon.place(relx=0.5, rely=0.5, anchor="center")
        lbl = tk.Label(f, text=name, font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_CARD, anchor="center", justify="center")
        lbl.pack(pady=(4, 0))
        f.pack(side="left")
        self._widgets.append({"circle": c, "icon": icon, "name": lbl})

    def update_stage(self, idx: int, status: str) -> None:
        if idx < 0 or idx >= len(_STAGES):
            return
        self._statuses[idx] = status
        w = self._widgets[idx]
        color, bg, icon = _STATUS_COLOR.get(status, MUTED_GRAY), _STATUS_BG.get(status, "#1e2030"), _STATUS_ICON.get(status, "⏳")
        w["circle"].config(bg=bg, highlightbackground=color)
        w["icon"].config(text=icon, bg=bg, fg=color)

    def set_stage_active(self, idx: int) -> None:
        for i in range(len(_STAGES)):
            self.update_stage(i, "completed" if i < idx else ("in_progress" if i == idx else "waiting"))

    def mark_all_completed(self) -> None:
        for i in range(len(_STAGES)):
            self.update_stage(i, "completed")

    def mark_error(self, idx: int | None = None) -> None:
        if idx is not None:
            self.update_stage(idx, "error")
        else:
            for i in reversed(range(len(_STAGES))):
                if self._statuses[i] == "in_progress":
                    self.update_stage(i, "error"); return

    def reset(self) -> None:
        for i in range(len(_STAGES)):
            self.update_stage(i, "waiting")
