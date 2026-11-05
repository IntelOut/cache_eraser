"""Filesystem path helpers.

Provides Windows long-path support, containment checks and reparse-point
detection used by the scanner and deleter.
"""

import os
import stat
import sys

IS_WINDOWS = os.name == "nt"
_REPARSE_FLAG = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def resource_path(relative: str) -> str:
    """Return an absolute path to a bundled resource.

    Works both from source and from a PyInstaller one-file build.

    Args:
        relative: Resource path relative to the project root.

    Returns:
        Absolute filesystem path.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def extended_path(path: str) -> str:
    """Return a long-path-safe absolute path on Windows.

    On non-Windows platforms the absolute path is returned unchanged.

    Args:
        path: Any filesystem path.

    Returns:
        Path prefixed with the Windows extended-length marker when needed.
    """
    absolute = os.path.abspath(path)
    if not IS_WINDOWS or absolute.startswith("\\\\?\\"):
        return absolute
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute[2:]
    return "\\\\?\\" + absolute


def display_path(path: str) -> str:
    """Strip Windows extended-length prefixes for display purposes."""
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[8:]
    if path.startswith("\\\\?\\"):
        return path[4:]
    return path


def is_within(path: str, root: str) -> bool:
    """Return True when *path* resolves to a location inside *root*.

    Symlinks and junctions are resolved before comparison, so a link that
    points outside the root is rejected.

    Args:
        path: Candidate path.
        root: Directory that must contain *path*.

    Returns:
        ``True`` when the resolved path is the root or a descendant of it.
    """
    try:
        resolved_path = os.path.realpath(os.path.abspath(path))
        resolved_root = os.path.realpath(os.path.abspath(root))
        common = os.path.commonpath([resolved_path, resolved_root])
    except (OSError, ValueError):
        return False
    return os.path.normcase(common) == os.path.normcase(resolved_root)


def is_reparse_or_link(path: str) -> bool:
    """Return True for symlinks, junctions and other reparse points.

    Following such paths during scanning or deletion is unsafe because the
    target may live outside the scanned root.

    Args:
        path: Filesystem path to inspect.

    Returns:
        ``True`` when the path is a link-like object.
    """
    try:
        if os.path.islink(path):
            return True
        is_junction = getattr(os.path, "isjunction", None)
        if is_junction is not None and is_junction(path):
            return True
        if not IS_WINDOWS:
            return False
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
        return bool(attributes & _REPARSE_FLAG)
    except OSError:
        return False
