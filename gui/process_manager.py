"""
LinkeVagas GUI — Process Manager.

Wraps ``subprocess.Popen`` to launch the agent pipeline as a child process,
captures stdout/stderr in a background thread, and exposes callbacks for the
GUI to consume output and lifecycle events without blocking the main thread.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Pipeline stage detection patterns
# ─────────────────────────────────────────────────────────────────────────────

# Maps substrings found in stdout → pipeline stage index (0-based).
_STAGE_MARKERS: list[tuple[str, int]] = [
    ("Buscando vagas:",       0),   # Stage 1: Buscar Vagas
    ("[1/5] Analisando",      1),   # Stage 2: Analisar ATS
    ("[2/5] Acionando",       2),   # Stage 3: Ler Currículo
    ("[3/5] Reescrevendo",    3),   # Stage 4: Otimizar CV
    ("[4/5] Convertendo",     4),   # Stage 5: Converter PDF
    ("[5/5] Acionando",       5),   # Stage 6: Enviar Candidatura
]


def detect_stage(line: str) -> Optional[int]:
    """Return a 0-based stage index if *line* triggers a stage transition."""
    for marker, idx in _STAGE_MARKERS:
        if marker in line:
            return idx
    return None


def is_pipeline_complete(line: str) -> bool:
    """Return True if the line signals pipeline completion."""
    return "Pipeline concluído" in line


# ─────────────────────────────────────────────────────────────────────────────
# AgentProcess
# ─────────────────────────────────────────────────────────────────────────────

class AgentProcess:
    """
    Manages the lifecycle of a ``python -m src.agents.agent`` subprocess.

    Parameters
    ----------
    project_root:
        Absolute path to the LinkeVagas project directory.
    on_output:
        Callback ``(line: str) -> None`` invoked for every stdout/stderr line.
    on_stage:
        Callback ``(stage_index: int) -> None`` invoked when a pipeline stage
        transition is detected.
    on_complete:
        Callback ``() -> None`` invoked when the process exits with code 0 and
        the "Pipeline concluído" marker was seen.
    on_error:
        Callback ``(returncode: int) -> None`` invoked on non-zero exit or
        unexpected termination.
    """

    def __init__(
        self,
        project_root: str | Path,
        on_output:   Callable[[str], None]  = lambda _l: None,
        on_stage:    Callable[[int], None]   = lambda _s: None,
        on_complete: Callable[[], None]      = lambda: None,
        on_error:    Callable[[int], None]   = lambda _r: None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.on_output   = on_output
        self.on_stage    = on_stage
        self.on_complete = on_complete
        self.on_error    = on_error

        self._proc: Optional[subprocess.Popen[str]] = None
        self._thread: Optional[threading.Thread] = None
        self._stopped = threading.Event()

    # ── public API ──────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> None:
        """Launch the agent pipeline subprocess."""
        if self.is_running:
            return

        self._stopped.clear()

        # Prefer the project's virtual-env Python so that all dependencies
        # (playwright, agno, etc.) are available, even if the GUI itself was
        # launched with the system Python.
        venv_python = self.project_root / ".venv" / "bin" / "python"
        python = str(venv_python) if venv_python.is_file() else sys.executable

        self._proc = subprocess.Popen(
            [python, "-m", "src.agents.agent"],
            cwd=str(self.project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,                # Line-buffered
            env={**os.environ},       # Inherit env (dotenv is loaded at agent level)
        )

        self._thread = threading.Thread(
            target=self._read_output,
            name="agent-output-reader",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Gracefully stop the subprocess (SIGTERM → wait → SIGKILL)."""
        self._stopped.set()
        proc = self._proc
        if proc is None:
            return
        if proc.poll() is not None:
            return

        try:
            # Try graceful termination first.
            if sys.platform == "win32":
                proc.terminate()
            else:
                os.kill(proc.pid, signal.SIGTERM)

            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        except OSError:
            pass

    # ── internal ────────────────────────────────────────────────────────

    def _read_output(self) -> None:
        """Background thread: reads stdout line-by-line and fires callbacks."""
        assert self._proc is not None
        assert self._proc.stdout is not None

        pipeline_done = False

        try:
            for line in self._proc.stdout:
                if self._stopped.is_set():
                    break

                line = line.rstrip("\n").rstrip("\r")
                self.on_output(line)

                stage = detect_stage(line)
                if stage is not None:
                    self.on_stage(stage)

                if is_pipeline_complete(line):
                    pipeline_done = True

        except Exception:
            pass
        finally:
            proc = self._proc
            if proc is not None:
                proc.wait()
                rc = proc.returncode

                if self._stopped.is_set():
                    # User requested stop — treat as non-error.
                    self.on_output("⏹ Processo interrompido pelo usuário.")
                elif pipeline_done or rc == 0:
                    self.on_complete()
                else:
                    self.on_error(rc if rc is not None else -1)

            self._proc = None
