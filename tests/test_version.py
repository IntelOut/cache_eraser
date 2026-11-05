"""Tests for version metadata consistency."""

from pathlib import Path

from cache_eraser import __version__

ROOT = Path(__file__).resolve().parents[1]


class TestVersion:
    """The package version and the Windows metadata must not drift."""

    def test_version_info_matches_package(self):
        text = (ROOT / "version_info.txt").read_text(encoding="utf-8")
        major, minor, patch = __version__.split(".")
        assert f"filevers=({major}, {minor}, {patch}, 0)" in text
        assert f"prodvers=({major}, {minor}, {patch}, 0)" in text
        assert f"'FileVersion', '{__version__}'" in text
        assert f"'ProductVersion', '{__version__}'" in text
