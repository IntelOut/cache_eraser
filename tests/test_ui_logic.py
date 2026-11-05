"""Tests for UI state helpers that do not require a display."""

from cache_eraser.scanner import ScanItem
from cache_eraser.ui_logic import close_action, deletion_allowed

ITEM = ScanItem("C:\\cache", "__pycache__", 10)


class TestDeletionAllowed:
    """Deletion must be enabled only for complete, idle, non-dry scans."""

    def test_empty_results(self):
        assert not deletion_allowed([], False, False, False)

    def test_complete_scan(self):
        assert deletion_allowed([ITEM], False, False, False)

    def test_busy(self):
        assert not deletion_allowed([ITEM], True, False, False)

    def test_dry_run(self):
        assert not deletion_allowed([ITEM], False, True, False)

    def test_incomplete_scan(self):
        assert not deletion_allowed([ITEM], False, False, True)


class TestCloseAction:
    """Closing must never interrupt an in-flight deletion."""

    def test_blocked_while_deleting(self):
        assert close_action(True, True) == "blocked"

    def test_confirm_while_scanning(self):
        assert close_action(False, True) == "confirm"

    def test_close_when_idle(self):
        assert close_action(False, False) == "close"
