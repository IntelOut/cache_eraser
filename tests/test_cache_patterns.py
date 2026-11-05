"""Tests for cache pattern definitions."""

from pathlib import Path

from cache_eraser.patterns import (
    ALL_PATTERN_IDS,
    CACHE_PATTERNS,
    DEFAULT_SELECTED_IDS,
    EXCLUDED_DIRS,
    PATTERNS_BY_ID,
    RISK_CAUTION,
    RISK_SAFE,
    CachePattern,
)


class TestCachePatterns:
    """Validate cache pattern definitions and invariants."""

    def test_all_patterns_have_required_fields(self):
        """Every pattern must have id, label, description and a match rule."""
        for pattern in CACHE_PATTERNS:
            assert pattern.id
            assert pattern.label
            assert pattern.description
            assert pattern.category
            assert pattern.dir_names or pattern.dir_patterns or pattern.file_patterns

    def test_all_pattern_ids_are_unique(self):
        """No two patterns may share the same id."""
        ids = [pattern.id for pattern in CACHE_PATTERNS]
        assert len(ids) == len(set(ids))

    def test_all_pattern_ids_match_constant(self):
        """ALL_PATTERN_IDS must be the flattened list of pattern ids."""
        assert ALL_PATTERN_IDS == [pattern.id for pattern in CACHE_PATTERNS]

    def test_readme_pattern_count_matches(self):
        """The advertised cache type count must stay in sync with the code."""
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
        assert f"**{len(CACHE_PATTERNS)} типов кеша**" in readme

    def test_patterns_by_id_is_consistent(self):
        """PATTERNS_BY_ID must map every id to its pattern."""
        assert set(PATTERNS_BY_ID) == set(ALL_PATTERN_IDS)
        for pattern_id, pattern in PATTERNS_BY_ID.items():
            assert pattern.id == pattern_id

    def test_risk_values_are_known(self):
        """Every pattern must use a supported risk level."""
        for pattern in CACHE_PATTERNS:
            assert pattern.risk in {RISK_SAFE, RISK_CAUTION}

    def test_default_selection_contains_only_safe_patterns(self):
        """Risky patterns must not be selected by default."""
        for pattern in CACHE_PATTERNS:
            assert (pattern.id in DEFAULT_SELECTED_IDS) == pattern.is_safe()

    def test_egg_info_is_a_directory_pattern(self):
        """*.egg-info matches directories, so it needs a dir pattern."""
        eggs = PATTERNS_BY_ID["eggs"]
        assert "*.egg-info" in eggs.dir_patterns
        assert "*.egg-info" not in eggs.file_patterns

    def test_excluded_dirs_are_lowercase(self):
        """Excluded directory names are normalized for case folding."""
        for directory in EXCLUDED_DIRS:
            assert directory == directory.lower()

    def test_excluded_dirs_contains_critical_entries(self):
        """.git and node_modules must always be excluded."""
        assert ".git" in EXCLUDED_DIRS
        assert "node_modules" in EXCLUDED_DIRS

    def test_excluded_dirs_no_empty_strings(self):
        """Exclusion set must not contain empty strings."""
        assert "" not in EXCLUDED_DIRS

    def test_dataclass_defaults(self):
        """CachePattern should default optional collections and risk."""
        pattern = CachePattern(id="test", label="Test", description="A test pattern")
        assert not pattern.dir_names
        assert not pattern.dir_patterns
        assert not pattern.file_patterns
        assert pattern.risk == RISK_SAFE
        assert pattern.is_safe()
