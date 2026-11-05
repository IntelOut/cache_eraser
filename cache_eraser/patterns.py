"""Cache artifact definitions for Cache Eraser.

Each pattern describes one cache type: how it is matched, how risky it is
to delete, and which project category it belongs to.
"""

from dataclasses import dataclass, field

RISK_SAFE = "safe"
RISK_CAUTION = "caution"


@dataclass
class CachePattern:
    """Describe a single cache artifact type.

    Attributes:
        id: Unique machine-readable identifier.
        label: Human-readable name shown in the UI.
        description: Explanation of what this cache type is.
        category: Project ecosystem the pattern belongs to.
        dir_names: Exact directory names that match this pattern.
        dir_patterns: Glob-style directory name patterns.
        file_patterns: Glob-style file patterns.
        risk: ``"safe"`` when deleting is harmless, ``"caution"`` otherwise.
    """

    id: str
    label: str
    description: str
    dir_names: list[str] = field(default_factory=list)
    dir_patterns: list[str] = field(default_factory=list)
    file_patterns: list[str] = field(default_factory=list)
    risk: str = RISK_SAFE
    category: str = "Python"

    def is_safe(self) -> bool:
        """Return True when the pattern is safe enough to be enabled by default."""
        return self.risk == RISK_SAFE


CACHE_PATTERNS: list[CachePattern] = [
    CachePattern(
        "__pycache__",
        "__pycache__",
        "Python bytecode cache directories",
        dir_names=["__pycache__"],
    ),
    CachePattern(
        "pyc",
        "*.pyc / *.pyo",
        "Standalone compiled Python files",
        file_patterns=["*.pyc", "*.pyo"],
    ),
    CachePattern(
        "mypy_cache",
        ".mypy_cache",
        "Mypy type checker cache",
        dir_names=[".mypy_cache"],
    ),
    CachePattern(
        "pytest_cache",
        ".pytest_cache",
        "Pytest cache",
        dir_names=[".pytest_cache"],
    ),
    CachePattern(
        "ruff_cache",
        ".ruff_cache",
        "Ruff linter cache",
        dir_names=[".ruff_cache"],
    ),
    CachePattern(
        "hypothesis",
        ".hypothesis",
        "Hypothesis testing cache",
        dir_names=[".hypothesis"],
    ),
    CachePattern(
        "htmlcov",
        "htmlcov",
        "Coverage HTML reports",
        dir_names=["htmlcov"],
    ),
    CachePattern(
        "coverage",
        ".coverage / coverage.xml",
        "Coverage data and XML reports",
        file_patterns=[".coverage", "coverage.xml"],
    ),
    CachePattern(
        "tox_nox",
        ".tox / .nox",
        "Tox and Nox virtual environments",
        dir_names=[".tox", ".nox"],
    ),
    CachePattern(
        "eggs",
        ".eggs / *.egg-info",
        "Python egg artifacts",
        dir_names=[".eggs"],
        dir_patterns=["*.egg-info"],
        file_patterns=["*.egg"],
    ),
    CachePattern(
        "ipynb",
        ".ipynb_checkpoints",
        "Jupyter notebook checkpoints",
        dir_names=[".ipynb_checkpoints"],
    ),
    CachePattern(
        "pyre_pytype",
        ".pyre / .pytype",
        "Python type checker caches",
        dir_names=[".pyre", ".pytype"],
    ),
    CachePattern(
        "cython_debug",
        "cython_debug",
        "Cython debug symbols",
        dir_names=["cython_debug"],
    ),
    CachePattern(
        "pdm_build",
        ".pdm-build / __pypackages__",
        "PDM build artifacts and local packages",
        dir_names=[".pdm-build", "__pypackages__"],
    ),
    CachePattern(
        "scrapy",
        ".scrapy",
        "Scrapy cache",
        dir_names=[".scrapy"],
    ),
    CachePattern(
        "cache_dir",
        ".cache",
        "Generic application cache directory",
        dir_names=[".cache"],
        risk=RISK_CAUTION,
        category="Generic",
    ),
    CachePattern(
        "next",
        ".next",
        "Next.js build cache",
        dir_names=[".next"],
        category="JavaScript",
    ),
    CachePattern(
        "turbo",
        ".turbo",
        "Turborepo cache",
        dir_names=[".turbo"],
        category="JavaScript",
    ),
    CachePattern(
        "angular",
        ".angular",
        "Angular CLI cache",
        dir_names=[".angular"],
        category="JavaScript",
    ),
    CachePattern(
        "nuxt",
        ".nuxt",
        "Nuxt build cache",
        dir_names=[".nuxt"],
        category="JavaScript",
    ),
    CachePattern(
        "svelte_kit",
        ".svelte-kit",
        "SvelteKit build cache",
        dir_names=[".svelte-kit"],
        category="JavaScript",
    ),
    CachePattern(
        "parcel",
        ".parcel-cache",
        "Parcel bundler cache",
        dir_names=[".parcel-cache"],
        category="JavaScript",
    ),
    CachePattern(
        "webpack",
        ".webpack",
        "Webpack cache",
        dir_names=[".webpack"],
        category="JavaScript",
    ),
    CachePattern(
        "nyc",
        ".nyc_output",
        "Istanbul/NYC coverage output",
        dir_names=[".nyc_output"],
        category="JavaScript",
    ),
    CachePattern(
        "tsbuildinfo",
        "*.tsbuildinfo",
        "TypeScript incremental build info",
        file_patterns=["*.tsbuildinfo"],
        category="JavaScript",
    ),
    CachePattern(
        "eslint",
        ".eslintcache",
        "ESLint cache file",
        file_patterns=[".eslintcache"],
        category="JavaScript",
    ),
    CachePattern(
        "stylelint",
        ".stylelintcache",
        "Stylelint cache file",
        file_patterns=[".stylelintcache"],
        category="JavaScript",
    ),
    CachePattern(
        "build",
        "build/",
        "Generic build output directories",
        dir_names=["build"],
        risk=RISK_CAUTION,
        category="Build",
    ),
    CachePattern(
        "rust_target",
        "target/",
        "Rust and Maven build output",
        dir_names=["target"],
        risk=RISK_CAUTION,
        category="Build",
    ),
    CachePattern(
        "gradle",
        ".gradle",
        "Gradle project cache",
        dir_names=[".gradle"],
        category="Build",
    ),
    CachePattern(
        "dotnet_obj",
        "obj/",
        ".NET intermediate build output",
        dir_names=["obj"],
        risk=RISK_CAUTION,
        category="Build",
    ),
    CachePattern(
        "pods",
        "Pods/",
        "CocoaPods dependencies and build cache",
        dir_names=["Pods"],
        risk=RISK_CAUTION,
        category="Mobile",
    ),
    CachePattern(
        "derived_data",
        "DerivedData/",
        "Xcode derived data",
        dir_names=["DerivedData"],
        category="Mobile",
    ),
    CachePattern(
        "dart_tool",
        ".dart_tool",
        "Dart and Flutter tool cache",
        dir_names=[".dart_tool"],
        category="Mobile",
    ),
    CachePattern(
        "terraform",
        ".terraform",
        "Terraform provider and module cache",
        dir_names=[".terraform"],
        category="Infrastructure",
    ),
    CachePattern(
        "serverless",
        ".serverless",
        "Serverless Framework cache",
        dir_names=[".serverless"],
        category="Infrastructure",
    ),
    CachePattern(
        "aws_sam",
        ".aws-sam",
        "AWS SAM build cache",
        dir_names=[".aws-sam"],
        category="Infrastructure",
    ),
]

EXCLUDED_DIRS: set[str] = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "output",
}

ALL_PATTERN_IDS: list[str] = [p.id for p in CACHE_PATTERNS]
DEFAULT_SELECTED_IDS: list[str] = [p.id for p in CACHE_PATTERNS if p.is_safe()]
PATTERNS_BY_ID: dict[str, CachePattern] = {p.id: p for p in CACHE_PATTERNS}
