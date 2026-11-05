"""Tests for the filesystem scanner."""

import os
import threading
from typing import cast

from cache_eraser.patterns import CachePattern
from cache_eraser.scanner import (
    ScanStats,
    _build_dir_map,
    _build_dir_patterns,
    _build_file_map,
    _handle_entry,
    _make_matchers,
    _measure_entry,
    get_dir_size,
    scan_directory,
)


class FakeLinkEntry:
    """Minimal DirEntry stand-in for a symbolic link."""

    name = "link.txt"
    path = "C:\\link.txt"

    def is_symlink(self) -> bool:
        return True

    def is_dir(  # pylint: disable=unused-argument
        self, follow_symlinks: bool = False
    ) -> bool:
        return False

    def is_file(  # pylint: disable=unused-argument
        self, follow_symlinks: bool = False
    ) -> bool:
        return False

    def stat(self, follow_symlinks: bool = False) -> os.stat_result:
        raise AssertionError("stat must not be called for links")


class TestBuildMaps:
    """Tests for pattern lookup helpers."""

    def test_build_dir_map_is_case_folded(self):
        patterns = [
            CachePattern("a", "A", "desc", dir_names=["Dir_A"]),
            CachePattern("b", "B", "desc", dir_names=["dir_b", "dir_c"]),
        ]
        assert _build_dir_map(patterns) == {
            "dir_a": "a",
            "dir_b": "b",
            "dir_c": "b",
        }

    def test_build_dir_patterns(self):
        patterns = [CachePattern("a", "A", "desc", dir_patterns=["*.EGG-INFO"])]
        assert _build_dir_patterns(patterns) == [("*.egg-info", "a")]

    def test_build_file_map(self):
        patterns = [
            CachePattern("a", "A", "desc", file_patterns=["*.pyc"]),
            CachePattern("b", "B", "desc", file_patterns=["*.PYO", "*.egg"]),
        ]
        assert _build_file_map(patterns) == [
            ("*.pyc", "a"),
            ("*.pyo", "b"),
            ("*.egg", "b"),
        ]

    def test_empty_patterns(self):
        assert not _build_dir_map([])
        assert not _build_dir_patterns([])
        assert not _build_file_map([])


class TestGetDirSize:
    """Tests for recursive directory size calculation."""

    def test_empty_dir(self, tmp_path):
        assert get_dir_size(str(tmp_path)) == 0

    def test_dir_with_files(self, tmp_path):
        (tmp_path / "a.txt").write_bytes(b"x" * 100)
        nested = tmp_path / "sub"
        nested.mkdir()
        (nested / "b.txt").write_bytes(b"y" * 200)
        assert get_dir_size(str(tmp_path)) == 300

    def test_nonexistent_path(self):
        assert get_dir_size("C:\\nonexistent_path_xyz") == 0


class TestScanDirectory:
    """Tests for recursive directory scanning."""

    def test_no_cache_found(self, tmp_path):
        (tmp_path / "src").mkdir()
        assert not scan_directory(str(tmp_path), {"__pycache__"})

    def test_finds_pycache(self, tmp_path):
        cache = tmp_path / "src" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "foo.pyc").write_bytes(b"x" * 50)
        results = scan_directory(str(tmp_path), {"__pycache__"})
        assert len(results) == 1
        assert results[0].pattern_id == "__pycache__"
        assert results[0].size == 50

    def test_finds_cache_case_insensitively(self, tmp_path):
        cache = tmp_path / "UPPER"
        cache.mkdir()
        cache = cache / "__PYCACHE__"
        cache.mkdir()
        (cache / "foo.pyc").write_bytes(b"x" * 10)
        results = scan_directory(str(tmp_path), {"__pycache__"})
        assert len(results) == 1
        assert results[0].pattern_id == "__pycache__"

    def test_finds_file_pattern_case_insensitively(self, tmp_path):
        (tmp_path / "module.PYC").write_bytes(b"x" * 10)
        results = scan_directory(str(tmp_path), {"pyc"})
        assert [item.pattern_id for item in results] == ["pyc"]

    def test_finds_egg_info_directory(self, tmp_path):
        (tmp_path / "package.egg-info").mkdir()
        (tmp_path / "package.egg-info" / "PKG-INFO").write_text("x", encoding="utf-8")
        results = scan_directory(str(tmp_path), {"eggs"})
        assert len(results) == 1
        assert results[0].pattern_id == "eggs"
        assert results[0].size == 1

    def test_skips_excluded_dirs(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "__pycache__").mkdir()
        assert not scan_directory(str(tmp_path), {"__pycache__"})

    def test_excluded_dirs_are_case_insensitive(self, tmp_path):
        modules = tmp_path / "NODE_MODULES"
        modules.mkdir()
        (modules / "__pycache__").mkdir()
        assert not scan_directory(str(tmp_path), {"__pycache__"})

    def test_empty_selected_ids(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        assert not scan_directory(str(tmp_path), set())

    def test_matched_parent_hides_nested_match(self, tmp_path):
        nested = tmp_path / ".cache" / ".pytest_cache"
        nested.mkdir(parents=True)
        results = scan_directory(str(tmp_path), {"cache_dir", "pytest_cache"})
        assert len(results) == 1
        assert results[0].pattern_id == "cache_dir"

    def test_progress_callback_reports_directories(self, tmp_path):
        (tmp_path / "one").mkdir()
        (tmp_path / "two").mkdir()
        calls = []
        scan_directory(
            str(tmp_path),
            {"__pycache__"},
            progress=lambda count, current: calls.append((count, current)),
        )
        assert calls
        assert calls[-1][0] == 3

    def test_cancel_stops_scan(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        cancel = threading.Event()
        cancel.set()
        scan_stats = ScanStats()
        results = scan_directory(str(tmp_path), {"__pycache__"}, cancel=cancel, stats=scan_stats)
        assert not results
        assert scan_stats.cancelled

    def test_link_is_skipped(self, tmp_path, make_link):
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "__pycache__").mkdir()
        make_link(outside, root / "link")
        results = scan_directory(str(root), {"__pycache__"})
        assert not results

    def test_unreadable_root_is_reported(self, tmp_path):
        file_path = tmp_path / "file.txt"
        file_path.write_text("x", encoding="utf-8")
        stats = ScanStats()
        results = scan_directory(str(file_path), {"__pycache__"}, stats=stats)
        assert not results
        assert stats.skipped == 1
        assert stats.errors

    def test_link_file_is_reported(self):
        stats = ScanStats()
        results = []
        entry = cast("os.DirEntry[str]", FakeLinkEntry())
        child = _handle_entry(entry, _make_matchers([]), results, stats, None)
        assert child is None
        assert not results
        assert stats.skipped == 1
        assert "Skipped link" in stats.errors[0]

    def test_measure_entry_skips_links(self):
        stats = ScanStats()
        stack = []
        entry = cast("os.DirEntry[str]", FakeLinkEntry())
        assert _measure_entry(entry, stats, set(), stack) == 0
        assert stats.skipped == 1
        assert not stack

    def test_measure_skips_excluded_dirs(self, tmp_path):
        cache = tmp_path / ".cache"
        cache.mkdir()
        (cache / "keep.bin").write_bytes(b"x" * 10)
        excluded = cache / "node_modules"
        excluded.mkdir()
        (excluded / "skip.bin").write_bytes(b"y" * 100)
        results = scan_directory(str(tmp_path), {"cache_dir"})
        assert len(results) == 1
        assert results[0].size == 10
