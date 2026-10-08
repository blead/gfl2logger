"""Platform-specific defaults for process-scoped local traffic capture."""

from __future__ import annotations

import platform


PROCESS_NAMES = {
    "Darwin": "SnqxExilium",
    "Windows": "GF2_Exilium",
}


def default_capture_mode(system: str | None = None) -> str:
    """Return the mitmproxy local-mode spec for the current platform."""
    system = system or platform.system()
    try:
        process_name = PROCESS_NAMES[system]
    except KeyError as e:
        supported = ", ".join(sorted(PROCESS_NAMES))
        raise RuntimeError(
            f"Unsupported platform {system!r}; supported platforms: {supported}"
        ) from e
    return f"local:{process_name}"
