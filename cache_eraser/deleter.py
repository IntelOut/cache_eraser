"""Deletion helpers with containment checks and optional Recycle Bin support."""

import os
import shutil
import stat
from collections.abc import Callable
from dataclasses import dataclass, field

from cache_eraser.paths import (
    IS_WINDOWS,
    display_path,
    extended_path,
    is_reparse_or_link,
    is_within,
)

ProgressCallback = Callable[[int, str], None]


@dataclass
class DeleteReport:
    """Outcome of a delete operation."""

    success: int = 0
    errors: int = 0
    trashed: int = 0
    deleted: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Return the number of processed items."""
        return self.success + self.errors

    def add_error(self, message: str) -> None:
        """Record an error while keeping the message list bounded."""
        self.errors += 1
        if len(self.messages) < 100:
            self.messages.append(message)


def _is_cancelled(cancel: object | None) -> bool:
    """Return True when the cancel event is set."""
    is_set = getattr(cancel, "is_set", None)
    return bool(is_set()) if callable(is_set) else False


def _make_tree_writable(path: str) -> None:
    """Best-effort removal of the read-only attribute in a directory tree.

    Links and junctions are skipped: ``os.chmod`` follows them, so touching
    a link must never modify a target outside the deleted tree. The walk
    uses cached ``DirEntry`` type information and avoids an extra stat per
    regular file.
    """
    stack = [extended_path(path)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if is_reparse_or_link(entry.path):
                                continue
                            stack.append(entry.path)
                        elif not entry.is_file(follow_symlinks=False):
                            continue
                    except OSError:
                        continue
                    try:
                        os.chmod(entry.path, stat.S_IWRITE)
                    except OSError:
                        pass
        except OSError:
            pass


def _remove_permanently(path: str) -> None:
    """Delete a file or directory tree from disk."""
    target = extended_path(path)
    if os.path.isdir(target):
        _make_tree_writable(target)
        shutil.rmtree(target)
    else:
        try:
            os.chmod(target, stat.S_IWRITE)
        except OSError:
            pass
        os.remove(target)


def _send_to_trash(path: str) -> None:
    """Move a path to the operating system Recycle Bin."""
    target = os.path.normpath(os.path.abspath(display_path(path)))
    if IS_WINDOWS and len(target) >= 260:
        raise OSError("path is too long for the Recycle Bin; use permanent deletion instead")
    try:
        from send2trash import (  # pylint: disable=import-outside-toplevel
            send2trash,
        )
    except ImportError as exc:
        raise OSError("send2trash is not installed") from exc
    send2trash(target)


def delete_items(
    items: list[str],
    root: str | None = None,
    use_trash: bool = False,
    progress: ProgressCallback | None = None,
    cancel: object | None = None,
) -> DeleteReport:
    """Delete files and directories, refusing unsafe targets.

    Targets that resolve outside *root* or that are symlinks/junctions are
    refused. Read-only files are made writable before permanent deletion.

    Args:
        items: Absolute paths to delete.
        root: Scanned root directory used for containment checks.
        use_trash: Move items to the Recycle Bin instead of deleting.
        progress: Optional callback receiving ``(index, path)``.
        cancel: Optional object with an ``is_set()`` method.

    Returns:
        A :class:`DeleteReport` describing the outcome.
    """
    report = DeleteReport()
    for index, item in enumerate(items, start=1):
        if _is_cancelled(cancel):
            break
        if progress is not None:
            progress(index, item)

        if root is not None and not is_within(item, root):
            report.add_error(f"Refused (outside root): {item}")
            continue

        if is_reparse_or_link(item):
            report.add_error(f"Refused (link/junction): {item}")
            continue

        try:
            if use_trash:
                _send_to_trash(item)
                report.trashed += 1
            else:
                _remove_permanently(item)
            report.success += 1
            report.deleted.append(item)
        except OSError as exc:
            report.add_error(f"{display_path(item)}: {exc}")

    return report
