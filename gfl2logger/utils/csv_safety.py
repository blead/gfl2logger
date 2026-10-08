from typing import Any


FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def spreadsheet_safe(value: Any) -> Any:
    """Neutralize strings that spreadsheet applications may treat as formulas."""
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value
