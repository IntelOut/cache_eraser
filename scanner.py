"""Filesystem scanner for Cache Eraser.

Provides recursive directory scanning to find cache artifacts,
directory size calculation, and safe deletion with read-only handling.
"""

import fnmatch
import os
import shutil
import stat

from cache_patterns import CACHE_PATTERNS, EXCLUDED_DIRS, CachePattern


ScanResult = list[tuple[str, str, int]]


def get_dir_size(path: str) -> int:
    """Calculate total size of all files in a directory tree.

    Args:
        path: Directory to measure.

    Returns:
        Total size in bytes. Returns 0 on permission errors.
    """
    total = 0
    try:
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def format_size(size_bytes: int) -> str:
    """Format byte count into a human-readable string (B/KB/MB/GB).

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted string like ``"1.5 MB"``.
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    return f"{size_bytes / 1024 ** 3:.1f} GB"


def _build_dir_map(patterns: list[CachePattern]) -> dict[str, str]:
    """Build a dict mapping directory name -> cache pattern id."""
    m: dict[str, str] = {}
    for p in patterns:
        for d in p.dir_names:
            m[d] = p.id
    return m


def _build_file_map(patterns: list[CachePattern]) -> list[tuple[str, str]]:
    """Build a list of (glob_pattern, pattern_id) for file matching."""
    result: list[tuple[str, str]] = []
    for p in patterns:
        for pat in p.file_patterns:
            result.append((pat, p.id))
    return result


def scan_directory(
    root_path: str,
    selected_ids: set[str],
) -> ScanResult:
    """Recursively scan *root_path* for cache artifacts matching *selected_ids*.

    Skips directories listed in :data:`cache_patterns.EXCLUDED_DIRS`.
    Matched directories are not descended into.

    Args:
        root_path: Directory to start scanning from.
        selected_ids: Cache pattern ids to look for.

    Returns:
        List of ``(absolute_path, pattern_id, size_bytes)`` tuples.
    """
    patterns = [p for p in CACHE_PATTERNS if p.id in selected_ids]
    dir_map = _build_dir_map(patterns)
    file_map = _build_file_map(patterns)
    results: ScanResult = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]

        for d in dirnames[:]:
            if d in dir_map:
                full = os.path.join(dirpath, d)
                size = get_dir_size(full)
                results.append((full, dir_map[d], size))
                dirnames.remove(d)

        for f in filenames:
            full = os.path.join(dirpath, f)
            for pat, pid in file_map:
                if fnmatch.fnmatch(f, pat):
                    try:
                        size = os.path.getsize(full)
                    except (OSError, PermissionError):
                        size = 0
                    results.append((full, pid, size))
                    break

    return results


def delete_items(items: list[str]) -> tuple[int, int]:
    """Delete a list of file or directory paths.

    Read-only files on Windows are made writable before deletion.

    Args:
        items: Absolute paths to delete.

    Returns:
        ``(success_count, error_count)``.
    """
    success = 0
    errors = 0
    for path in items:
        try:
            if os.path.isdir(path):
                for dirpath, _, filenames in os.walk(path):
                    for f in filenames:
                        os.chmod(os.path.join(dirpath, f), stat.S_IWRITE)
                shutil.rmtree(path)
            else:
                os.remove(path)
            success += 1
        except (OSError, PermissionError):
            errors += 1
    return success, errors
