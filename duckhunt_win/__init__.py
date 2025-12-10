"""DuckHunt - Prevent RubberDucky and keystroke injection attacks."""

try:
    from ._version import __version__
except ImportError:
    # This should not happen if installed correctly, but for safety:
    __version__ = "0.0.0"

