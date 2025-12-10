"""DuckHunt - Prevent RubberDucky and keystroke injection attacks."""

try:
    from importlib.metadata import version
    __version__ = version("duckhunt-win")
except Exception:
    __version__ = "0.10.0"  # Fallback for development
