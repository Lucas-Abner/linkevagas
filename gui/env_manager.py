"""
LinkeVagas GUI — .env File Manager.

Provides helpers to read / write environment variables from / to the project's
`.env` file using python-dotenv (already an indirect dependency of the project).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

try:
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover
    dotenv_values = None  # type: ignore[assignment]


# Variables managed by the GUI — order matters for display.
MANAGED_VARS = [
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "LINKEDIN_EMAIL",
    "LINKEDIN_PASSWORD",
    "BUSCAR_VAGA",
    "QUANTIDADE_VAGAS",
    "LOCAL_BUSCA",
    "MODELO_PRINCIPAL",
    "CV_PATH",
]


def _default_env_path() -> Path:
    """Return the path to the project-root `.env` file."""
    return Path(__file__).resolve().parent.parent / ".env"


def load_env_vars(env_path: Optional[str | Path] = None) -> Dict[str, str]:
    """
    Read all key=value pairs from the `.env` file.

    Returns a dict with at least the keys in ``MANAGED_VARS`` (set to empty
    string if absent).
    """
    path = Path(env_path) if env_path else _default_env_path()

    values: Dict[str, str] = {}
    if path.exists():
        if dotenv_values is not None:
            raw = dotenv_values(str(path))
            values = {k: (v or "") for k, v in raw.items()}
        else:
            # Minimal fallback parser when python-dotenv isn't installed.
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    values[key.strip()] = val.strip()

    # Guarantee all managed keys exist.
    for key in MANAGED_VARS:
        values.setdefault(key, "")

    return values


def save_env_vars(
    new_values: Dict[str, str],
    env_path: Optional[str | Path] = None,
) -> None:
    """
    Write *new_values* into the `.env` file, preserving any extra variables and
    comments that the GUI does not manage.

    Strategy:
    1.  Read the existing file line by line.
    2.  For every line whose key is in *new_values*, replace the value.
    3.  Append any keys from *new_values* that were not already in the file.
    4.  Write everything back.
    """
    path = Path(env_path) if env_path else _default_env_path()

    existing_lines: list[str] = []
    if path.exists():
        existing_lines = path.read_text(encoding="utf-8").splitlines()

    seen_keys: set[str] = set()
    output_lines: list[str] = []

    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, _, _ = stripped.partition("=")
            key = key.strip()
            if key in new_values:
                output_lines.append(f"{key}={new_values[key]}")
                seen_keys.add(key)
                continue
        output_lines.append(line)

    # Append keys that weren't already present.
    for key, val in new_values.items():
        if key not in seen_keys:
            output_lines.append(f"{key}={val}")

    # Ensure trailing newline.
    text = "\n".join(output_lines)
    if not text.endswith("\n"):
        text += "\n"

    path.write_text(text, encoding="utf-8")
