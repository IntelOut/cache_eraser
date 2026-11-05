"""Tests for safe deletion."""

# pylint: disable=protected-access

import os
import stat
import sys
import threading

import pytest

from cache_eraser.deleter import (
    DeleteReport,
    _make_tree_writable,
    _send_to_trash,
    delete_items,
)
from cache_eraser.paths import display_path


class TestDeleteItems:
    """Tests for files, directories and safety refusals."""

    def test_delete_file(self, tmp_path):
        target = tmp_path / "test.txt"
        target.write_text("hello", encoding="utf-8")
        report = delete_items([str(target)], root=str(tmp_path))
        assert report.success == 1
        assert report.errors == 0
        assert report.deleted == [str(target)]
        assert not target.exists()

    def test_delete_directory(self, tmp_path):
        directory = tmp_path / "subdir"
        directory.mkdir()
        (directory / "file.txt").write_text("hello", encoding="utf-8")
        report = delete_items([str(directory)], root=str(tmp_path))
        assert report.success == 1
        assert not directory.exists()

    def test_nonexistent_path_counts_as_error(self):
        report = delete_items(["C:\\nonexistent_path_xyz"])
        assert report.success == 0
        assert report.errors == 1
        assert report.total == 1

    def test_outside_root_is_refused(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "outside.txt"
        outside.write_text("keep", encoding="utf-8")
        report = delete_items([str(outside)], root=str(root))
        assert report.errors == 1
        assert report.success == 0
        assert outside.exists()

    def test_read_only_file_is_deleted(self, tmp_path):
        target = tmp_path / "readonly.txt"
        target.write_text("data", encoding="utf-8")
        os.chmod(target, stat.S_IREAD)
        try:
            report = delete_items([str(target)], root=str(tmp_path))
        finally:
            if target.exists():
                os.chmod(target, stat.S_IWRITE)
        assert report.success == 1
        assert not target.exists()

    def test_cancel_stops_before_deletion(self, tmp_path):
        target = tmp_path / "keep.txt"
        target.write_text("keep", encoding="utf-8")
        cancel = threading.Event()
        cancel.set()
        report = delete_items([str(target)], root=str(tmp_path), cancel=cancel)
        assert report.total == 0
        assert target.exists()

    def test_trash_is_used_when_requested(self, tmp_path, monkeypatch):
        target = tmp_path / "trash.txt"
        target.write_text("data", encoding="utf-8")
        moved = []
        monkeypatch.setattr("cache_eraser.deleter._send_to_trash", moved.append)
        report = delete_items([str(target)], root=str(tmp_path), use_trash=True)
        assert report.success == 1
        assert report.trashed == 1
        assert moved == [str(target)]

    def test_link_is_refused(self, tmp_path, make_link):
        target = tmp_path / "target"
        target.mkdir()
        keep = target / "keep.txt"
        keep.write_text("data", encoding="utf-8")
        link = tmp_path / "link"
        make_link(target, link)
        report = delete_items([str(link)], root=str(tmp_path))
        assert report.errors == 1
        assert keep.exists()

    def test_progress_callback(self, tmp_path):
        target = tmp_path / "file.txt"
        target.write_text("data", encoding="utf-8")
        calls = []
        report = delete_items(
            [str(target)],
            root=str(tmp_path),
            progress=lambda index, path: calls.append((index, path)),
        )
        assert report.success == 1
        assert calls == [(1, str(target))]

    def test_missing_send2trash_is_reported(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "send2trash", None)
        with pytest.raises(OSError):
            _send_to_trash("anywhere")

    def test_trash_rejects_long_windows_path(self, monkeypatch):
        monkeypatch.setattr("cache_eraser.deleter.IS_WINDOWS", True)
        with pytest.raises(OSError, match="too long"):
            _send_to_trash("C:\\" + "a" * 300)

    def test_writable_walk_does_not_follow_links(self, tmp_path, make_link, monkeypatch):
        outside = tmp_path / "outside"
        outside.mkdir()
        outside_file = outside / "keep.txt"
        outside_file.write_text("keep", encoding="utf-8")

        root = tmp_path / "root"
        root.mkdir()
        inside_file = root / "inside.txt"
        inside_file.write_text("data", encoding="utf-8")
        make_link(outside, root / "link")

        touched = []
        monkeypatch.setattr(
            "cache_eraser.deleter.os.chmod",
            lambda path, mode: touched.append(os.path.normcase(display_path(path))),
        )
        _make_tree_writable(str(root))

        assert os.path.normcase(str(inside_file)) in touched
        assert os.path.normcase(str(outside_file)) not in touched

    def test_nested_link_target_is_not_deleted(self, tmp_path, make_link):
        outside = tmp_path / "outside"
        outside.mkdir()
        keep = outside / "keep.txt"
        keep.write_text("keep", encoding="utf-8")

        root = tmp_path / "root"
        root.mkdir()
        (root / "inside.txt").write_text("data", encoding="utf-8")
        make_link(outside, root / "link")

        report = delete_items([str(root)], root=str(tmp_path))
        assert report.success == 1
        assert not root.exists()
        assert keep.exists()

    def test_report_total(self):
        report = DeleteReport(success=2, errors=3)
        assert report.total == 5
        report.add_error("boom")
        assert report.errors == 4
        assert report.messages == ["boom"]
