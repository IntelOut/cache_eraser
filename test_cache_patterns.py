"""Tests for cache_patterns module."""

import pytest
from cache_patterns import CACHE_PATTERNS, EXCLUDED_DIRS, ALL_PATTERN_IDS, CachePattern


class TestCachePatterns:
    def test_all_patterns_have_required_fields(self):
        for p in CACHE_PATTERNS:
            assert p.id, f"Pattern missing id: {p}"
            assert p.label, f"Pattern {p.id} missing label"
            assert p.description, f"Pattern {p.id} missing description"
            assert p.dir_names or p.file_patterns, f"Pattern {p.id} has no dir or file patterns"

    def test_all_pattern_ids_are_unique(self):
        ids = [p.id for p in CACHE_PATTERNS]
        assert len(ids) == len(set(ids)), "Duplicate pattern ids found"

    def test_all_pattern_ids_match_constant(self):
        assert ALL_PATTERN_IDS == [p.id for p in CACHE_PATTERNS]

    def test_excluded_dirs_are_lowercase(self):
        for d in EXCLUDED_DIRS:
            assert d == d.lower(), f"Excluded dir '{d}' should be lowercase"

    def test_excluded_dirs_contains_git(self):
        assert ".git" in EXCLUDED_DIRS

    def test_excluded_dirs_no_empty_strings(self):
        assert "" not in EXCLUDED_DIRS

    def test_cache_pattern_dataclass_defaults(self):
        p = CachePattern(id="test", label="Test", description="A test pattern")
        assert p.dir_names == []
        assert p.file_patterns == []

    def test_cache_pattern_rejects_both_empty(self):
        for pattern in CACHE_PATTERNS:
            assert pattern.dir_names or pattern.file_patterns
