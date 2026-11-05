"""Pure UI state helpers that do not depend on tkinter."""

from cache_eraser.scanner import ScanItem


def deletion_allowed(
    items: list[ScanItem],
    busy: bool,
    dry_run: bool,
    incomplete: bool,
) -> bool:
    """Return True when deletion actions may be enabled."""
    return bool(items) and not busy and not dry_run and not incomplete


def close_action(deleting: bool, busy: bool) -> str:
    """Return ``"blocked"``, ``"confirm"`` or ``"close"`` for window closing."""
    if deleting:
        return "blocked"
    if busy:
        return "confirm"
    return "close"
