"""DuckHunt - Prevent RubberDucky and keystroke injection attacks."""
import sys

if sys.platform != 'win32':
    raise OSError("Only Windows is supported")


try:
    from ._version import __version__
except ImportError:
    # This should not happen if installed correctly, but for safety:
    __version__ = "0.0.0"

