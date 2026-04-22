"""
LinkeVagas GUI — LinkedIn Session Panel.

Shows the status of ``linkedin_session.json`` and provides buttons to verify
or renew the session.
"""

from __future__ import annotations

import json
import os
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from gui.theme import (
    ACCENT_BLUE, BG_CARD, BG_INPUT, BORDER, ERROR_RED, FONT_BODY,
    FONT_BUTTON, FONT_SMALL, FONT_SUBHEADING, MUTED_GRAY,
    SUCCESS_GREEN, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, WARNING_AMBER,
)


def _session_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "linkedin_session.json"


def _check_session() -> tuple[str, str, str]:
    """
    Inspect ``linkedin_session.json``.

    Returns ``(status, label_text, colour)`` where *status* is one of
    ``"valid"``, ``"expired"``, ``"missing"``.
    """
    path = _session_path()
    if not path.exists():
        return "missing", "❌  Sem sessão", ERROR_RED

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "missing", "❌  Arquivo corrompido", ERROR_RED

    for cookie in data.get("cookies", []):
        if cookie.get("name") == "li_at":
            expires = cookie.get("expires", -1)
            if expires != -1 and expires < time.time():
                return "expired", "⚠️  Sessão expirada", WARNING_AMBER
            return "valid", "✅  Sessão válida", SUCCESS_GREEN

    return "expired", "⚠️  Cookie li_at ausente", WARNING_AMBER


class SessionPanel(ttk.Frame):
    """LinkedIn session status indicator + renew button."""

    def __init__(self, parent: tk.Widget, **kw) -> None:
        super().__init__(parent, style="Card.TFrame", **kw)
        self._build()
        self.refresh()

    def _build(self) -> None:
        outer = tk.Frame(self, bg=BG_CARD)
        outer.pack(fill="x", padx=16, pady=12)

        tk.Label(outer, text="🔗  Sessão LinkedIn", font=FONT_SUBHEADING,
                 fg=ACCENT_BLUE, bg=BG_CARD, anchor="w").pack(anchor="w", pady=(0, 10))

        # Status row
        status_row = tk.Frame(outer, bg=BG_CARD)
        status_row.pack(fill="x")

        self._status_label = tk.Label(
            status_row, text="…", font=FONT_BODY,
            fg=MUTED_GRAY, bg=BG_CARD, anchor="w",
        )
        self._status_label.pack(side="left")

        # Buttons
        btn_row = tk.Frame(outer, bg=BG_CARD)
        btn_row.pack(fill="x", pady=(10, 0))

        tk.Button(
            btn_row, text="🔃 Verificar", font=FONT_SMALL,
            bg=BG_INPUT, fg=TEXT_PRIMARY, relief="flat", cursor="hand2",
            padx=10, pady=4, command=self.refresh,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            btn_row, text="🔄 Renovar Sessão", font=FONT_SMALL,
            bg=WARNING_AMBER, fg="#ffffff", relief="flat", cursor="hand2",
            padx=10, pady=4, command=self._on_renew,
        ).pack(side="left")

    def refresh(self) -> None:
        _, text, color = _check_session()
        self._status_label.config(text=text, fg=color)

    def _on_renew(self) -> None:
        path = _session_path()
        if path.exists():
            confirm = messagebox.askyesno(
                "Renovar Sessão",
                "Isso apagará linkedin_session.json.\n"
                "Na próxima execução do pipeline, o navegador abrirá para um novo login.\n\n"
                "Continuar?",
            )
            if not confirm:
                return
            try:
                path.unlink()
            except OSError:
                pass

        self.refresh()
        messagebox.showinfo(
            "Sessão Renovada",
            "O arquivo de sessão foi removido.\n"
            "Ao iniciar o pipeline, o navegador abrirá para que você faça login no LinkedIn.",
        )
