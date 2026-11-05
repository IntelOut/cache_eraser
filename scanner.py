"""Backward-compatible re-exports for the scanner module."""

from cache_eraser.deleter import DeleteReport, delete_items
from cache_eraser.formatter import format_size
from cache_eraser.scanner import (
    ScanItem,
    ScanResult,
    ScanStats,
    _build_dir_map,
    _build_dir_patterns,
    _build_file_map,
    get_dir_size,
    scan_directory,
)

__all__ = [
    "DeleteReport",
    "ScanItem",
    "ScanResult",
    "ScanStats",
    "_build_dir_map",
    "_build_dir_patterns",
    "_build_file_map",
    "delete_items",
    "format_size",
    "get_dir_size",
    "scan_directory",
]
