"""Tests for path helpers."""

import os

from cache_eraser import paths as paths_module
from cache_eraser.paths import (
    IS_WINDOWS,
    display_path,
    extended_path,
    is_reparse_or_link,
    is_within,
    resource_path,
)


class TestExtendedPath:
    """Tests for Windows long-path handling."""

    def test_returns_absolute_path(self, tmp_path):
        assert os.path.isabs(extended_path(str(tmp_path)))

    def test_windows_prefix(self, tmp_path):
        result = extended_path(str(tmp_path))
        if IS_WINDOWS:
            assert result.startswith("\\\\?\\")
        else:
            assert not result.startswith("\\\\?\\")

    def test_idempotent_on_windows(self, tmp_path):
        once = extended_path(str(tmp_path))
        assert extended_path(once) == once

    def test_display_strips_prefix(self):
        assert display_path("\\\\?\\C:\\temp") == "C:\\temp"
        assert display_path("\\\\?\\UNC\\server\\share") == "\\\\server\\share"
        assert display_path("C:\\temp") == "C:\\temp"


class TestIsWithin:
    """Tests for containment checks."""

    def test_child_is_within_root(self, tmp_path):
        child = tmp_path / "a" / "b"
        child.mkdir(parents=True)
        assert is_within(str(child), str(tmp_path))

    def test_root_is_within_itself(self, tmp_path):
        assert is_within(str(tmp_path), str(tmp_path))

    def test_sibling_is_outside(self, tmp_path):
        root = tmp_path / "root"
        sibling = tmp_path / "other"
        root.mkdir()
        sibling.mkdir()
        assert not is_within(str(sibling), str(root))

    def test_missing_path_inside_root_is_within(self, tmp_path):
        assert is_within(str(tmp_path / "missing"), str(tmp_path))


class TestReparse:
    """Tests for link detection."""

    def test_regular_file_is_not_link(self, tmp_path):
        target = tmp_path / "file.txt"
        target.write_text("hello", encoding="utf-8")
        assert not is_reparse_or_link(str(target))

    def test_symlink_is_detected(self, monkeypatch):
        monkeypatch.setattr(paths_module.os.path, "islink", lambda _path: True)
        assert is_reparse_or_link("anything")

    def test_oserror_is_handled(self, monkeypatch):
        def raise_error(_path):
            raise OSError("boom")

        monkeypatch.setattr(paths_module.os.path, "islink", raise_error)
        assert not is_reparse_or_link("anything")


class TestIsWithinErrors:
    """Containment checks must never raise on unusual paths."""

    def test_value_error_returns_false(self, monkeypatch, tmp_path):
        def raise_error(_paths):
            raise ValueError("different drives")

        monkeypatch.setattr(paths_module.os.path, "commonpath", raise_error)
        assert not is_within(str(tmp_path), str(tmp_path))


class TestResourcePath:
    """Tests for bundled resource resolution."""

    def test_points_to_existing_icon(self):
        assert os.path.isfile(resource_path("icon.png"))
