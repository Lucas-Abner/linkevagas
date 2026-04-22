"""
LinkeVagas GUI — Configuration Panel.

Provides a form to view and edit all user-configurable environment variables
stored in the project's `.env` file.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog
from typing import TYPE_CHECKING, Dict

from gui.theme import (
    ACCENT_BLUE, BG_CARD, BG_INPUT, BORDER, FONT_BODY, FONT_BUTTON,
    FONT_SMALL, FONT_SUBHEADING, MUTED_GRAY, SUCCESS_GREEN, TEXT_MUTED,
    TEXT_PRIMARY, TEXT_SECONDARY, ERROR_RED,
)
from gui.env_manager import load_env_vars, save_env_vars

if TYPE_CHECKING:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# Field descriptors
# ─────────────────────────────────────────────────────────────────────────────

_FIELDS = [
    {
        "key": "OPENAI_API_KEY",
        "label": "🔑  OpenAI API Key",
        "type": "password",
        "hint": "sk-proj-…",
    },
    {
        "key": "GOOGLE_API_KEY",
        "label": "🔑  Google Gemini API Key",
        "type": "password",
        "hint": "(opcional)",
    },
    {
        "key": "LINKEDIN_EMAIL",
        "label": "📧  E-mail LinkedIn",
        "type": "text",
        "hint": "seu@email.com",
    },
    {
        "key": "LINKEDIN_PASSWORD",
        "label": "🔒  Senha LinkedIn",
        "type": "password",
        "hint": "",
    },
    {
        "key": "BUSCAR_VAGA",
        "label": "🔍  Termo de Busca",
        "type": "text",
        "hint": 'Ex: "Agente de IA"',
    },
    {
        "key": "QUANTIDADE_VAGAS",
        "label": "📊  Quantidade de Vagas",
        "type": "spinbox",
        "hint": "",
    },
    {
        "key": "MODELO_PRINCIPAL",
        "label": "🤖  Modelo Principal",
        "type": "combo",
        "hint": "",
        "options": ["gpt-4o", "gpt-4o-mini", "qwen2.5:7b"],
    },
    {
        "key": "CV_PATH",
        "label": "📄  Currículo (PDF)",
        "type": "file",
        "hint": "Selecione o seu currículo em PDF",
    },
]


class ConfigPanel(ttk.Frame):
    """Configuration panel showing all editable .env variables."""

    def __init__(self, parent: tk.Widget, **kw) -> None:
        super().__init__(parent, style="Card.TFrame", **kw)
        self._entries: Dict[str, tk.Variable] = {}
        self._password_entries: Dict[str, ttk.Entry] = {}
        self._show_states: Dict[str, bool] = {}
        self._toast_label: tk.Label | None = None
        self._build()
        self._load()

    # ── build ───────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Header
        header = tk.Frame(self, bg=BG_CARD)
        header.pack(fill="x", padx=16, pady=(16, 4))
        tk.Label(
            header, text="⚙️  Configuração", font=FONT_SUBHEADING,
            fg=ACCENT_BLUE, bg=BG_CARD, anchor="w",
        ).pack(side="left")

        # Scrollable area
        container = tk.Frame(self, bg=BG_CARD)
        container.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        for field in _FIELDS:
            self._add_field(container, field)

        # Save button
        btn_frame = tk.Frame(self, bg=BG_CARD)
        btn_frame.pack(fill="x", padx=16, pady=(4, 16))

        self._save_btn = tk.Button(
            btn_frame,
            text="💾  Salvar Configurações",
            font=FONT_BUTTON,
            bg=ACCENT_BLUE,
            fg="#ffffff",
            activebackground="#6da3ff",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            padx=16, pady=8,
            command=self._on_save,
        )
        self._save_btn.pack(fill="x")

        # Toast area
        self._toast_label = tk.Label(
            btn_frame, text="", font=FONT_SMALL, bg=BG_CARD,
            fg=SUCCESS_GREEN, anchor="center",
        )
        self._toast_label.pack(fill="x", pady=(6, 0))

    def _add_field(self, parent: tk.Widget, field: dict) -> None:
        """Create a labelled input row for one .env variable."""
        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(fill="x", pady=(8, 0))

        # Label
        lbl_text = field["label"]
        if field["key"] == "GOOGLE_API_KEY":
            lbl_text += "  (opcional)"
        tk.Label(
            row, text=lbl_text, font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_CARD, anchor="w",
        ).pack(anchor="w")

        # Input container
        input_frame = tk.Frame(row, bg=BG_CARD)
        input_frame.pack(fill="x", pady=(2, 0))

        ftype = field["type"]

        if ftype == "combo":
            var = tk.StringVar()
            combo = ttk.Combobox(
                input_frame, textvariable=var,
                values=field.get("options", []),
                font=FONT_BODY,
            )
            combo.pack(fill="x", side="left", expand=True)
            self._entries[field["key"]] = var

        elif ftype == "spinbox":
            var = tk.StringVar(value="1")
            spin = tk.Spinbox(
                input_frame, from_=1, to=100, textvariable=var,
                font=FONT_BODY, bg=BG_INPUT, fg=TEXT_PRIMARY,
                insertbackground=TEXT_PRIMARY,
                relief="flat", bd=0, highlightthickness=1,
                highlightbackground=BORDER, highlightcolor=ACCENT_BLUE,
                width=8, buttonbackground=BG_CARD,
            )
            spin.pack(side="left", padx=(0, 4))
            self._entries[field["key"]] = var

        elif ftype == "password":
            var = tk.StringVar()
            entry = tk.Entry(
                input_frame, textvariable=var, show="●",
                font=FONT_BODY, bg=BG_INPUT, fg=TEXT_PRIMARY,
                insertbackground=TEXT_PRIMARY,
                relief="flat", bd=0, highlightthickness=1,
                highlightbackground=BORDER, highlightcolor=ACCENT_BLUE,
            )
            entry.pack(side="left", fill="x", expand=True, ipady=4)
            self._entries[field["key"]] = var
            self._password_entries[field["key"]] = entry
            self._show_states[field["key"]] = False

            toggle_btn = tk.Button(
                input_frame, text="👁", font=FONT_SMALL,
                bg=BG_CARD, fg=TEXT_MUTED, relief="flat",
                cursor="hand2", width=3,
                command=lambda k=field["key"]: self._toggle_password(k),
            )
            toggle_btn.pack(side="right", padx=(4, 0))

        elif ftype == "file":
            var = tk.StringVar()
            entry = tk.Entry(
                input_frame, textvariable=var,
                font=FONT_BODY, bg=BG_INPUT, fg=TEXT_PRIMARY,
                insertbackground=TEXT_PRIMARY,
                relief="flat", bd=0, highlightthickness=1,
                highlightbackground=BORDER, highlightcolor=ACCENT_BLUE,
            )
            entry.pack(side="left", fill="x", expand=True, ipady=4)
            self._entries[field["key"]] = var

            browse_btn = tk.Button(
                input_frame, text="📂 Procurar", font=FONT_SMALL,
                bg=BG_INPUT, fg=TEXT_PRIMARY, relief="flat",
                cursor="hand2", padx=8,
                command=lambda v=var: self._browse_file(v),
            )
            browse_btn.pack(side="right", padx=(4, 0))

        else:
            # Plain text entry
            var = tk.StringVar()
            entry = tk.Entry(
                input_frame, textvariable=var,
                font=FONT_BODY, bg=BG_INPUT, fg=TEXT_PRIMARY,
                insertbackground=TEXT_PRIMARY,
                relief="flat", bd=0, highlightthickness=1,
                highlightbackground=BORDER, highlightcolor=ACCENT_BLUE,
            )
            entry.pack(side="left", fill="x", expand=True, ipady=4)
            self._entries[field["key"]] = var

        # Hint
        if field.get("hint"):
            tk.Label(
                row, text=field["hint"], font=FONT_SMALL,
                fg=TEXT_MUTED, bg=BG_CARD, anchor="w",
            ).pack(anchor="w", pady=(1, 0))

    # ── actions ─────────────────────────────────────────────────────────

    def _toggle_password(self, key: str) -> None:
        entry = self._password_entries[key]
        self._show_states[key] = not self._show_states[key]
        entry.config(show="" if self._show_states[key] else "●")

    def _browse_file(self, var: tk.StringVar) -> None:
        """Open a file dialog to select a PDF file."""
        path = filedialog.askopenfilename(
            title="Selecione o seu currículo",
            filetypes=[("PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
        )
        if path:
            var.set(path)

    def _load(self) -> None:
        """Load values from .env into the form fields."""
        values = load_env_vars()
        for key, var in self._entries.items():
            val = values.get(key, "")
            var.set(val)

    def _on_save(self) -> None:
        """Write current form values to .env."""
        new_values: Dict[str, str] = {}
        for key, var in self._entries.items():
            new_values[key] = var.get().strip()

        try:
            save_env_vars(new_values)
            self._show_toast("✅  Configurações salvas com sucesso!", SUCCESS_GREEN)
        except Exception as exc:
            self._show_toast(f"❌  Erro ao salvar: {exc}", ERROR_RED)

    def _show_toast(self, message: str, color: str) -> None:
        if self._toast_label:
            self._toast_label.config(text=message, fg=color)
            self.after(4000, lambda: self._toast_label.config(text=""))  # type: ignore[union-attr]
