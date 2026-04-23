#!/usr/bin/env python3
"""
LinkeVagas GUI — Entry Point.

Launch with::

    python gui/main.py

This script ensures the project root is on ``sys.path`` and the working
directory is set correctly so that ``.env`` and ``linkedin_session.json``
paths resolve as the existing code expects.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── resolve project root ────────────────────────────────────────────────────
# The GUI lives at <project_root>/gui/main.py, so the project root is one
# level up.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ensure project root is on sys.path so ``from gui…`` and ``from src…`` work.
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Set CWD to project root (the agent code uses relative paths for .env, etc.)
os.chdir(_PROJECT_ROOT)


def main() -> None:
    if len(sys.argv) > 1:
        if sys.argv[1] == "--run-agent":
            # Run the agent in headless mode
            import src.agents.agent
            sys.exit(0)
        elif sys.argv[1] == "--install-playwright":
            # Run the playwright installation process programmatically
            from playwright.__main__ import main as playwright_main
            sys.argv = ["playwright", "install", "chromium"]
            playwright_main()
            sys.exit(0)

    # Otherwise run the normal GUI
    from gui.app import App
    app = App()
    app.run()


if __name__ == "__main__":
    # Support for PyInstaller multiprocessing / subprocesses
    import multiprocessing
    multiprocessing.freeze_support()
    
    import sys
    import io
    
    # Forçar output em UTF-8 para não dar erro com os emojis no Windows (cp1252)
    if sys.stdout is not None:
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except AttributeError:
            pass
            
    if sys.stderr is not None:
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except AttributeError:
            pass

    main()
