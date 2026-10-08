"""Runtime paths that remain useful when the program is launched as an app."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

CONFIG_FILENAME = "gfl2logger.config.yaml"


def default_data_dir(
    *,
    system: str | None = None,
    frozen: bool | None = None,
    home: Path | None = None,
    cwd: Path | None = None,
) -> Path:
    """Return the directory used for configuration and exported data."""
    system = system or platform.system()
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen

    if system == "Darwin" and frozen:
        return (home or Path.home()).joinpath("gfl2logger")
    return cwd or Path.cwd()
