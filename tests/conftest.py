"""Shared pytest fixtures."""

import os
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest


@pytest.fixture
def make_link() -> Iterator[Callable[[Path, Path], str]]:
    """Create a symlink or, on Windows without privileges, a junction."""
    links: list[str] = []

    def _make(target: Path, link: Path) -> str:
        link_path = os.fspath(link)
        try:
            os.symlink(os.fspath(target), link_path, target_is_directory=os.path.isdir(target))
        except (OSError, NotImplementedError) as exc:
            if os.name != "nt":
                raise
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", link_path, os.fspath(target)],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise OSError(f"mklink failed: {result.stderr or result.stdout}") from exc
        links.append(link_path)
        return link_path

    yield _make

    for link_path in reversed(links):
        try:
            if os.path.isdir(link_path) and not os.path.islink(link_path):
                os.rmdir(link_path)
            else:
                os.unlink(link_path)
        except OSError:
            pass
