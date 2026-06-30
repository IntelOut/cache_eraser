"""Tests for cache_patterns module."""

from cache_patterns import CACHE_PATTERNS, EXCLUDED_DIRS, ALL_PATTERN_IDS, CachePattern


class TestCachePatterns:
    """Validate cache pattern definitions and invariants."""

    def test_all_patterns_have_required_fields(self):
        """Every pattern must have id, label, description, and at least one match rule."""
        for p in CACHE_PATTERNS:
            assert p.id, f"Pattern missing id: {p}"
            assert p.label, f"Pattern {p.id} missing label"
            assert p.description, f"Pattern {p.id} missing description"
            assert p.dir_names or p.file_patterns, f"Pattern {p.id} has no dir or file patterns"

    def test_all_pattern_ids_are_unique(self):
        """No two patterns may share the same id."""
        ids = [p.id for p in CACHE_PATTERNS]
        assert len(ids) == len(set(ids)), "Duplicate pattern ids found"

    def test_all_pattern_ids_match_constant(self):
        """ALL_PATTERN_IDS must be the flattened list of pattern ids."""
        assert ALL_PATTERN_IDS == [p.id for p in CACHE_PATTERNS]

    def test_excluded_dirs_are_lowercase(self):
        """All excluded directories should be lowercase for case-insensitive matching."""
        for d in EXCLUDED_DIRS:
            assert d == d.lower(), f"Excluded dir '{d}' should be lowercase"

    def test_excluded_dirs_contains_git(self):
        """.git must always be in the exclusion list."""
        assert ".git" in EXCLUDED_DIRS

    def test_excluded_dirs_no_empty_strings(self):
        """Exclusion set must not contain empty strings."""
        assert "" not in EXCLUDED_DIRS

    def test_cache_pattern_dataclass_defaults(self):
        """CachePattern should default dir_names and file_patterns to empty lists."""
        p = CachePattern(id="test", label="Test", description="A test pattern")
        assert not p.dir_names
        assert not p.file_patterns

    def test_cache_pattern_rejects_both_empty(self):
        """Every real pattern must match at least one directory or file pattern."""
        for pattern in CACHE_PATTERNS:
            assert pattern.dir_names or pattern.file_patterns
