"""Tests for scanner module."""

import os
import tempfile

from cache_patterns import CachePattern
from scanner import (
    _build_dir_map,
    _build_file_map,
    delete_items,
    format_size,
    get_dir_size,
    scan_directory,
)


class TestFormatSize:
    """Tests for human-readable size formatting."""

    def test_bytes(self):
        """Values under 1024 should display as raw bytes."""
        assert format_size(0) == "0 B"
        assert format_size(512) == "512 B"
        assert format_size(1023) == "1023 B"

    def test_kilobytes(self):
        """Values between 1 KiB and 1 MiB should display in KB."""
        assert format_size(1024) == "1.0 KB"
        assert format_size(1536) == "1.5 KB"

    def test_megabytes(self):
        """Values between 1 MiB and 1 GiB should display in MB."""
        assert format_size(1024 ** 2) == "1.0 MB"
        assert format_size(1024 ** 2 * 2) == "2.0 MB"

    def test_gigabytes(self):
        """Values above 1 GiB should display in GB."""
        assert format_size(1024 ** 3) == "1.0 GB"
        assert format_size(1024 ** 3 * 3) == "3.0 GB"


class TestBuildDirMap:
    """Tests for the internal _build_dir_map helper."""

    def test_build_dir_map(self):
        """Directory names should map to their pattern ids."""
        patterns = [
            CachePattern("a", "A", "desc", dir_names=["dir_a"]),
            CachePattern("b", "B", "desc", dir_names=["dir_b", "dir_c"]),
        ]
        m = _build_dir_map(patterns)
        assert m == {"dir_a": "a", "dir_b": "b", "dir_c": "b"}

    def test_empty_patterns(self):
        """An empty pattern list should produce an empty dict."""
        assert not _build_dir_map([])


class TestBuildFileMap:
    """Tests for the internal _build_file_map helper."""

    def test_build_file_map(self):
        """File globs should map to their pattern ids in order."""
        patterns = [
            CachePattern("a", "A", "desc", file_patterns=["*.pyc"]),
            CachePattern("b", "B", "desc", file_patterns=["*.pyo", "*.egg"]),
        ]
        m = _build_file_map(patterns)
        assert m == [("*.pyc", "a"), ("*.pyo", "b"), ("*.egg", "b")]

    def test_empty_patterns(self):
        """An empty pattern list should produce an empty list."""
        assert not _build_file_map([])


class TestGetDirSize:
    """Tests for recursive directory size calculation."""

    def test_empty_dir(self):
        """An empty directory should have size 0."""
        with tempfile.TemporaryDirectory() as tmp:
            assert get_dir_size(tmp) == 0

    def test_dir_with_files(self):
        """Size should be the sum of all file sizes within the tree."""
        with tempfile.TemporaryDirectory() as tmp:
            f1 = os.path.join(tmp, "a.txt")
            f2 = os.path.join(tmp, "sub", "b.txt")
            os.makedirs(os.path.dirname(f2))
            with open(f1, "wb") as f:
                f.write(b"x" * 100)
            with open(f2, "wb") as f:
                f.write(b"y" * 200)
            assert get_dir_size(tmp) == 300

    def test_nonexistent_path(self):
        """A non-existent path should return 0 without raising."""
        assert get_dir_size("C:\\nonexistent_path_xyz") == 0


class TestScanDirectory:
    """Tests for recursive directory scanning."""

    def test_no_cache_found(self):
        """A directory without cache artifacts should return an empty list."""
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "src"))
            results = scan_directory(tmp, {"__pycache__"})
            assert not results

    def test_finds_pycache(self):
        """.pycache directories should be detected and measured."""
        with tempfile.TemporaryDirectory() as tmp:
            pycache = os.path.join(tmp, "src", "__pycache__")
            os.makedirs(pycache)
            with open(os.path.join(pycache, "foo.pyc"), "wb") as f:
                f.write(b"x" * 50)
            results = scan_directory(tmp, {"__pycache__"})
            assert len(results) == 1
            _, pid, size = results[0]
            assert pid == "__pycache__"
            assert size == 50

    def test_skips_excluded_dirs(self):
        """Excluded directories like .git should never be descended into."""
        with tempfile.TemporaryDirectory() as tmp:
            git_dir = os.path.join(tmp, ".git")
            os.makedirs(git_dir)
            with open(os.path.join(git_dir, "HEAD"), "wb") as f:
                f.write(b"x" * 10)
            results = scan_directory(tmp, {"__pycache__"})
            assert not results

    def test_empty_selected_ids(self):
        """An empty selection set should return no results."""
        with tempfile.TemporaryDirectory() as tmp:
            results = scan_directory(tmp, set())
            assert not results


class TestDeleteItems:
    """Tests for safe file and directory deletion."""

    def test_delete_file(self):
        """A single file should be deleted successfully."""
        with tempfile.TemporaryDirectory() as tmp:
            f = os.path.join(tmp, "test.txt")
            with open(f, "w", encoding="utf-8") as fh:
                fh.write("hello")
            success, errors = delete_items([f])
            assert success == 1
            assert errors == 0
            assert not os.path.exists(f)

    def test_delete_directory(self):
        """A directory tree should be removed recursively."""
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "subdir")
            os.makedirs(d)
            with open(os.path.join(d, "file.txt"), "w", encoding="utf-8") as fh:
                fh.write("hello")
            success, errors = delete_items([d])
            assert success == 1
            assert errors == 0
            assert not os.path.exists(d)

    def test_delete_nonexistent(self):
        """Non-existent paths should count as errors."""
        success, errors = delete_items(["C:\\nonexistent_path_xyz"])
        assert success == 0
        assert errors == 1

    def test_delete_multiple_mixed(self):
        """Multiple valid files should all be deleted."""
        with tempfile.TemporaryDirectory() as tmp:
            f1 = os.path.join(tmp, "keep.txt")
            f2 = os.path.join(tmp, "delete.txt")
            with open(f1, "w", encoding="utf-8") as fh:
                fh.write("keep")
            with open(f2, "w", encoding="utf-8") as fh:
                fh.write("delete")
            success, errors = delete_items([f1, f2])
            assert success == 2
            assert errors == 0
