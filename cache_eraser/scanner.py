"""Filesystem scanner for Cache Eraser.

Recursively finds cache artifacts using :mod:`os.scandir`, supports
case-insensitive matching, Windows long paths, progress reporting,
cancellation and access-error collection.
"""

import fnmatch
import os
from collections.abc import Callable
from dataclasses import dataclass, field

from cache_eraser.paths import display_path, extended_path, is_reparse_or_link
from cache_eraser.patterns import CACHE_PATTERNS, EXCLUDED_DIRS, RISK_SAFE, CachePattern

ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True)
class ScanItem:
    """A single found cache artifact."""

    path: str
    pattern_id: str
    size: int
    risk: str = RISK_SAFE


ScanResult = list[ScanItem]


@dataclass
class ScanStats:
    """Statistics collected during a scan."""

    scanned_dirs: int = 0
    skipped: int = 0
    cancelled: bool = False
    errors: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Store an error message, keeping memory usage bounded."""
        if len(self.errors) < 100:
            self.errors.append(message)


def _build_dir_map(patterns: list[CachePattern]) -> dict[str, str]:
    """Build a case-folded mapping of directory name to pattern id."""
    mapping: dict[str, str] = {}
    for pattern in patterns:
        for name in pattern.dir_names:
            mapping[name.casefold()] = pattern.id
    return mapping


def _build_dir_patterns(patterns: list[CachePattern]) -> list[tuple[str, str]]:
    """Build a list of case-folded ``(glob, pattern_id)`` directory rules."""
    rules: list[tuple[str, str]] = []
    for pattern in patterns:
        for glob in pattern.dir_patterns:
            rules.append((glob.casefold(), pattern.id))
    return rules


def _build_file_map(patterns: list[CachePattern]) -> list[tuple[str, str]]:
    """Build a list of case-folded ``(glob, pattern_id)`` file rules."""
    rules: list[tuple[str, str]] = []
    for pattern in patterns:
        for glob in pattern.file_patterns:
            rules.append((glob.casefold(), pattern.id))
    return rules


def _match_dir(
    name: str,
    dir_map: dict[str, str],
    dir_patterns: list[tuple[str, str]],
) -> str | None:
    """Return the pattern id matching a directory name, if any."""
    key = name.casefold()
    matched = dir_map.get(key)
    if matched is not None:
        return matched
    for glob, pattern_id in dir_patterns:
        if fnmatch.fnmatchcase(key, glob):
            return pattern_id
    return None


def _match_file(name: str, file_map: list[tuple[str, str]]) -> str | None:
    """Return the pattern id matching a file name, if any."""
    key = name.casefold()
    for glob, pattern_id in file_map:
        if fnmatch.fnmatchcase(key, glob):
            return pattern_id
    return None


def get_dir_size(path: str) -> int:
    """Calculate the total size of all files in a directory tree.

    Args:
        path: Directory to measure.

    Returns:
        Total size in bytes. Permission errors are ignored.
    """
    return _measure_dir(path)


def _measure_entry(
    entry: os.DirEntry[str],
    stats: ScanStats | None,
    excluded_names: set[str],
    stack: list[str],
) -> int:
    """Return the file size for one entry and queue child directories."""
    try:
        if entry.is_symlink():
            if stats is not None:
                stats.skipped += 1
            return 0
        if entry.is_dir(follow_symlinks=False):
            if entry.name.casefold() in excluded_names:
                return 0
            if is_reparse_or_link(entry.path):
                if stats is not None:
                    stats.skipped += 1
                return 0
            stack.append(entry.path)
            return 0
        if entry.is_file(follow_symlinks=False):
            return entry.stat(follow_symlinks=False).st_size
    except OSError:
        if stats is not None:
            stats.skipped += 1
    return 0


def _measure_dir(
    path: str,
    stats: ScanStats | None = None,
    cancel: object | None = None,
    excluded: set[str] | None = None,
) -> int:
    """Measure a directory tree without following links or excluded dirs."""
    excluded_names = (
        excluded if excluded is not None else {name.casefold() for name in EXCLUDED_DIRS}
    )
    total = 0
    stack = [extended_path(path)]
    while stack:
        if _is_cancelled(cancel):
            return total
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    total += _measure_entry(entry, stats, excluded_names, stack)
        except OSError as exc:
            if stats is not None:
                stats.skipped += 1
                stats.add_error(f"{display_path(current)}: {exc}")
    return total


def _is_cancelled(cancel: object | None) -> bool:
    """Return True when the cancel event is set."""
    is_set = getattr(cancel, "is_set", None)
    return bool(is_set()) if callable(is_set) else False


@dataclass
class _Matchers:
    """Pre-computed pattern lookups shared by every scanned directory."""

    patterns_by_id: dict[str, CachePattern]
    dir_map: dict[str, str]
    dir_patterns: list[tuple[str, str]]
    file_map: list[tuple[str, str]]
    excluded: set[str]


def _make_matchers(patterns: list[CachePattern]) -> _Matchers:
    """Build all pattern lookup structures for one scan."""
    return _Matchers(
        patterns_by_id={pattern.id: pattern for pattern in patterns},
        dir_map=_build_dir_map(patterns),
        dir_patterns=_build_dir_patterns(patterns),
        file_map=_build_file_map(patterns),
        excluded={name.casefold() for name in EXCLUDED_DIRS},
    )


def _handle_dir_entry(
    entry: os.DirEntry[str],
    matchers: _Matchers,
    results: ScanResult,
    stats: ScanStats,
    cancel: object | None,
) -> str | None:
    """Handle a directory entry, returning it when it must be traversed."""
    if entry.name.casefold() in matchers.excluded:
        return None
    if is_reparse_or_link(entry.path):
        stats.skipped += 1
        stats.add_error(f"Skipped link/junction: {display_path(entry.path)}")
        return None
    pattern_id = _match_dir(entry.name, matchers.dir_map, matchers.dir_patterns)
    if pattern_id is None:
        return entry.path
    pattern = matchers.patterns_by_id[pattern_id]
    size = _measure_dir(entry.path, stats, cancel, matchers.excluded)
    results.append(ScanItem(display_path(entry.path), pattern_id, size, pattern.risk))
    return None


def _handle_file_entry(
    entry: os.DirEntry[str],
    matchers: _Matchers,
    results: ScanResult,
) -> None:
    """Record a matching file, if the entry matches any file pattern."""
    pattern_id = _match_file(entry.name, matchers.file_map)
    if pattern_id is None:
        return
    pattern = matchers.patterns_by_id[pattern_id]
    try:
        size = entry.stat(follow_symlinks=False).st_size
    except OSError:
        size = 0
    results.append(ScanItem(display_path(entry.path), pattern_id, size, pattern.risk))


def _handle_entry(
    entry: os.DirEntry[str],
    matchers: _Matchers,
    results: ScanResult,
    stats: ScanStats,
    cancel: object | None,
) -> str | None:
    """Classify one entry and return a child directory to visit."""
    try:
        is_symlink = entry.is_symlink()
        is_directory = entry.is_dir(follow_symlinks=False)
        is_file = entry.is_file(follow_symlinks=False)
    except OSError:
        stats.skipped += 1
        return None

    if is_symlink:
        stats.skipped += 1
        stats.add_error(f"Skipped link: {display_path(entry.path)}")
        return None
    if is_directory:
        return _handle_dir_entry(entry, matchers, results, stats, cancel)
    if is_file:
        _handle_file_entry(entry, matchers, results)
    return None


def _scan_one_dir(
    current: str,
    matchers: _Matchers,
    results: ScanResult,
    stats: ScanStats,
    cancel: object | None,
) -> list[str]:
    """Process one directory and return subdirectories left to visit."""
    try:
        with os.scandir(current) as iterator:
            entries = list(iterator)
    except OSError as exc:
        stats.skipped += 1
        stats.add_error(f"{display_path(current)}: {exc}")
        return []

    children: list[str] = []
    for entry in entries:
        child = _handle_entry(entry, matchers, results, stats, cancel)
        if child is not None:
            children.append(child)
    return children


def scan_directory(
    root_path: str,
    selected_ids: set[str],
    progress: ProgressCallback | None = None,
    cancel: object | None = None,
    stats: ScanStats | None = None,
) -> ScanResult:
    """Recursively scan *root_path* for cache artifacts.

    Matched directories are not descended into, which also removes nested
    duplicates when a parent cache directory matches a broader pattern.

    Args:
        root_path: Directory to start scanning from.
        selected_ids: Cache pattern ids to look for.
        progress: Optional callback receiving ``(dirs_scanned, current_path)``.
        cancel: Optional object with an ``is_set()`` method.
        stats: Optional statistics object filled during the scan.

    Returns:
        List of :class:`ScanItem` sorted by discovery order.
    """
    if stats is None:
        stats = ScanStats()

    patterns = [p for p in CACHE_PATTERNS if p.id in selected_ids]
    matchers = _make_matchers(patterns)
    results: ScanResult = []
    stack = [extended_path(root_path)]

    while stack:
        if _is_cancelled(cancel):
            stats.cancelled = True
            break

        current = stack.pop()
        stats.scanned_dirs += 1
        if progress is not None:
            progress(stats.scanned_dirs, display_path(current))
        stack.extend(_scan_one_dir(current, matchers, results, stats, cancel))

    return results
