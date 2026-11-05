"""Tests for human-readable size formatting."""

from cache_eraser.formatter import format_size


class TestFormatSize:
    """Tests for binary unit formatting."""

    def test_bytes(self):
        """Values under 1024 display as raw bytes."""
        assert format_size(0) == "0 B"
        assert format_size(512) == "512 B"
        assert format_size(1023) == "1023 B"

    def test_kibibytes(self):
        """1024-based units are labelled KiB, not KB."""
        assert format_size(1024) == "1.0 KiB"
        assert format_size(1536) == "1.5 KiB"

    def test_mebibytes(self):
        assert format_size(1024**2) == "1.0 MiB"
        assert format_size(1024**2 * 2) == "2.0 MiB"

    def test_gibibytes(self):
        assert format_size(1024**3) == "1.0 GiB"

    def test_rounding_crosses_unit_boundary(self):
        """1023.999 KiB rounds to 1.0 MiB, not 1024.0 KiB."""
        assert format_size(1024**2 - 1) == "1.0 MiB"

    def test_negative_is_clamped(self):
        """Negative sizes are treated as zero."""
        assert format_size(-5) == "0 B"
