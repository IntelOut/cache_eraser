"""Human-readable formatting helpers."""

_UNITS = ("KiB", "MiB", "GiB", "TiB", "PiB")


def format_size(size_bytes: int) -> str:
    """Format a byte count using binary (1024-based) units.

    Args:
        size_bytes: Size in bytes. Negative values are treated as zero.

    Returns:
        A string such as ``"1.5 MiB"``.
    """
    size = max(0, int(size_bytes))
    if size < 1024:
        return f"{size} B"
    value = float(size)
    for unit in _UNITS:
        value /= 1024
        if round(value, 1) < 1024 or unit == _UNITS[-1]:
            return f"{value:.1f} {unit}"
    return f"{value:.1f} {_UNITS[-1]}"  # pragma: no cover
