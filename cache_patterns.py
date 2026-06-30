"""Cache pattern definitions for Cache Eraser.

Defines which directories and file patterns are considered cache,
and which directories are excluded from scanning entirely.
"""

from dataclasses import dataclass, field


@dataclass
class CachePattern:
    """Describes a single cache artifact type.

    Attributes:
        id: Unique machine-readable identifier.
        label: Human-readable name shown in the UI.
        description: Explanation of what this cache type is.
        dir_names: Directory names that match this pattern.
        file_patterns: Glob-style file patterns that match this pattern.
    """
    id: str
    label: str
    description: str
    dir_names: list[str] = field(default_factory=list)
    file_patterns: list[str] = field(default_factory=list)


CACHE_PATTERNS: list[CachePattern] = [
    CachePattern("__pycache__", "__pycache__",
                 "Python bytecode cache directories", dir_names=["__pycache__"]),
    CachePattern("pyc", "*.pyc / *.pyo",
                 "Standalone compiled Python files", file_patterns=["*.pyc", "*.pyo"]),
    CachePattern("mypy_cache", ".mypy_cache",
                 "Mypy type checker cache", dir_names=[".mypy_cache"]),
    CachePattern("pytest_cache", ".pytest_cache",
                 "Pytest cache", dir_names=[".pytest_cache"]),
    CachePattern("ruff_cache", ".ruff_cache",
                 "Ruff linter cache", dir_names=[".ruff_cache"]),
    CachePattern("hypothesis", ".hypothesis",
                 "Hypothesis testing cache", dir_names=[".hypothesis"]),
    CachePattern("htmlcov", "htmlcov",
                 "Coverage HTML reports", dir_names=["htmlcov"]),
    CachePattern("build", "build/",
                 "Build output directories", dir_names=["build"]),
    CachePattern("next", ".next/",
                 "Next.js build cache", dir_names=[".next"]),
    CachePattern("turbo", ".turbo/",
                 "Turborepo cache", dir_names=[".turbo"]),
    CachePattern("cache_dir", ".cache/",
                 "Generic cache directories", dir_names=[".cache"]),
    CachePattern("dart_tool", ".dart_tool/",
                 "Dart/Flutter tool cache", dir_names=[".dart_tool"]),
    CachePattern("tox_nox", ".tox/ / .nox/",
                 "Tox/Nox virtual environments", dir_names=[".tox", ".nox"]),
    CachePattern("eggs", ".eggs/ / *.egg-info",
                 "Python egg artifacts", dir_names=[".eggs"],
                 file_patterns=["*.egg-info", "*.egg"]),
    CachePattern("ipynb", ".ipynb_checkpoints",
                 "Jupyter notebook checkpoints", dir_names=[".ipynb_checkpoints"]),
    CachePattern("pyre_pytype", ".pyre/ / .pytype/",
                 "Python type checker caches", dir_names=[".pyre", ".pytype"]),
    CachePattern("cython_debug", "cython_debug/",
                 "Cython debug symbols", dir_names=["cython_debug"]),
    CachePattern("pdm_build", ".pdm-build/ / __pypackages__",
                 "PDM build artifacts", dir_names=[".pdm-build", "__pypackages__"]),
    CachePattern("scrapy", ".scrapy/",
                 "Scrapy cache", dir_names=[".scrapy"]),
]

EXCLUDED_DIRS: set[str] = {".git", "node_modules", "venv", ".venv", "env", ".env", "dist", "output"}

ALL_PATTERN_IDS: list[str] = [p.id for p in CACHE_PATTERNS]
