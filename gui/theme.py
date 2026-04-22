"""
LinkeVagas GUI — Theme & Style Constants.

Centralised colour palette, font definitions, and ttk style configuration
used throughout the application.  Works with both ttkbootstrap (preferred)
and plain ttk (fallback).
"""

import tkinter as tk
from tkinter import ttk

# ─────────────────────────────────────────────────────────────────────────────
# Colour Palette (dark theme)
# ─────────────────────────────────────────────────────────────────────────────

BG_DARK       = "#0f1117"      # Main window background
BG_CARD       = "#1a1d27"      # Card / panel background
BG_INPUT      = "#252836"      # Entry / text input background
BORDER        = "#2e3140"      # Subtle border colour

ACCENT_BLUE   = "#4f8cff"      # Primary accent (buttons, links)
ACCENT_HOVER  = "#6da3ff"      # Button hover
SUCCESS_GREEN = "#2ecc71"      # Success indicators
WARNING_AMBER = "#f39c12"      # Warning / in-progress
ERROR_RED     = "#e74c3c"      # Error indicators
MUTED_GRAY    = "#6c7293"      # Muted / disabled text

TEXT_PRIMARY  = "#e8eaf0"      # Main text colour
TEXT_SECONDARY= "#a0a4b8"      # Secondary / label text
TEXT_MUTED    = "#6c7293"      # Placeholder / muted text

# ─────────────────────────────────────────────────────────────────────────────
# Fonts
# ─────────────────────────────────────────────────────────────────────────────

FONT_HEADING     = ("Segoe UI", 14, "bold")
FONT_SUBHEADING  = ("Segoe UI", 11, "bold")
FONT_BODY        = ("Segoe UI", 10)
FONT_SMALL       = ("Segoe UI", 9)
FONT_MONO        = ("Consolas", 10)
FONT_MONO_SMALL  = ("Consolas", 9)
FONT_BUTTON      = ("Segoe UI", 10, "bold")

# ─────────────────────────────────────────────────────────────────────────────
# Status colours (pipeline / badge)
# ─────────────────────────────────────────────────────────────────────────────

STATUS_COLORS = {
    "idle":       MUTED_GRAY,
    "waiting":    MUTED_GRAY,
    "running":    WARNING_AMBER,
    "in_progress":WARNING_AMBER,
    "done":       SUCCESS_GREEN,
    "completed":  SUCCESS_GREEN,
    "error":      ERROR_RED,
}

# ─────────────────────────────────────────────────────────────────────────────
# ttk Style Configuration (plain-ttk fallback)
# ─────────────────────────────────────────────────────────────────────────────

def configure_ttk_styles(root: tk.Tk) -> None:
    """Apply a dark style to standard ttk widgets when ttkbootstrap is absent."""
    style = ttk.Style(root)

    # Try using 'clam' as base — it supports most colour overrides.
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # General
    style.configure(".", background=BG_DARK, foreground=TEXT_PRIMARY,
                    fieldbackground=BG_INPUT, borderwidth=0,
                    font=FONT_BODY)

    # Frames
    style.configure("TFrame", background=BG_DARK)
    style.configure("Card.TFrame", background=BG_CARD)

    # Labels
    style.configure("TLabel", background=BG_DARK, foreground=TEXT_PRIMARY,
                    font=FONT_BODY)
    style.configure("Card.TLabel", background=BG_CARD)
    style.configure("Heading.TLabel", font=FONT_HEADING)
    style.configure("Sub.TLabel", font=FONT_SUBHEADING)
    style.configure("Muted.TLabel", foreground=TEXT_MUTED)

    # LabelFrame
    style.configure("TLabelframe", background=BG_CARD,
                    foreground=TEXT_PRIMARY, borderwidth=1, relief="solid")
    style.configure("TLabelframe.Label", background=BG_CARD,
                    foreground=ACCENT_BLUE, font=FONT_SUBHEADING)

    # Buttons
    style.configure("TButton", background=ACCENT_BLUE, foreground="#ffffff",
                    font=FONT_BUTTON, padding=(12, 6))
    style.map("TButton",
              background=[("active", ACCENT_HOVER), ("disabled", BORDER)],
              foreground=[("disabled", MUTED_GRAY)])

    style.configure("Success.TButton", background=SUCCESS_GREEN)
    style.map("Success.TButton",
              background=[("active", "#3ddf80"), ("disabled", BORDER)])

    style.configure("Danger.TButton", background=ERROR_RED)
    style.map("Danger.TButton",
              background=[("active", "#f55a4e"), ("disabled", BORDER)])

    # Entry
    style.configure("TEntry", fieldbackground=BG_INPUT,
                    foreground=TEXT_PRIMARY, insertcolor=TEXT_PRIMARY,
                    borderwidth=1, relief="solid", padding=(6, 4))

    # Combobox
    style.configure("TCombobox", fieldbackground=BG_INPUT,
                    foreground=TEXT_PRIMARY, padding=(6, 4))
    style.map("TCombobox",
              fieldbackground=[("readonly", BG_INPUT)],
              foreground=[("readonly", TEXT_PRIMARY)])

    # Spinbox
    style.configure("TSpinbox", fieldbackground=BG_INPUT,
                    foreground=TEXT_PRIMARY, padding=(6, 4))

    # Scrollbar
    style.configure("Vertical.TScrollbar",
                    background=BORDER, troughcolor=BG_DARK,
                    borderwidth=0, arrowsize=12)

    # Separator
    style.configure("TSeparator", background=BORDER)

    # Notebook (tabs)
    style.configure("TNotebook", background=BG_DARK, borderwidth=0)
    style.configure("TNotebook.Tab", background=BG_CARD,
                    foreground=TEXT_SECONDARY, padding=(14, 6),
                    font=FONT_BODY)
    style.map("TNotebook.Tab",
              background=[("selected", ACCENT_BLUE)],
              foreground=[("selected", "#ffffff")])
