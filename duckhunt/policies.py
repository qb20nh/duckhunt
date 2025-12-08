"""Protection policy implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from duckhunt.config import Config


class Policy(ABC):
    """Abstract base class for protection policies."""

    def __init__(self, config: Config) -> None:
        """Initialize policy with configuration.

        Args:
            config: DuckHunt configuration.
        """
        self.config = config
        self._log_path = Path(config.log_filename)
        self._prev_window: str = ""

    def log_event(self, window_name: str, key: str, ascii_code: int) -> None:
        """Log a keystroke event to the log file.

        Args:
            window_name: Name of the active window.
            key: Key name (e.g., 'A', 'Return').
            ascii_code: ASCII code of the key.
        """
        with self._log_path.open("a", encoding="utf-8") as f:
            if self._prev_window != window_name:
                f.write(f"\n[ {window_name} ]\n")
                self._prev_window = window_name

            if 32 < ascii_code < 127:
                f.write(chr(ascii_code))
            else:
                f.write(f"[{key}]")

    @abstractmethod
    def on_intrusion(self, window_name: str, key: str, ascii_code: int) -> bool:
        """Handle detected intrusion.

        Args:
            window_name: Name of the active window.
            key: Key name that triggered detection.
            ascii_code: ASCII code of the key.

        Returns:
            True to allow the keystroke, False to block it.
        """
        ...

    @abstractmethod
    def on_locked_keystroke(self, key: str, ascii_code: int) -> tuple[bool, bool]:
        """Handle keystroke while in locked state (paranoid mode).

        Args:
            key: Key name.
            ascii_code: ASCII code of the key.

        Returns:
            Tuple of (allow_keystroke, is_unlocked).
        """
        ...


class ParanoidPolicy(Policy):
    """Lock keyboard until password is entered."""

    def __init__(self, config: Config) -> None:
        """Initialize paranoid policy."""
        super().__init__(config)
        self._password_index = 0
        self._locked = False
        self._show_message: bool = True

    def on_intrusion(self, window_name: str, key: str, ascii_code: int) -> bool:
        """Lock keyboard and show warning message."""
        self._locked = True
        self._password_index = 0
        self._show_message = True
        return False

    def on_locked_keystroke(self, key: str, ascii_code: int) -> tuple[bool, bool]:
        """Check password input while locked."""
        if not self._locked:
            return True, True

        self.log_event("", key, ascii_code)

        password = self.config.password
        if ascii_code > 0 and chr(ascii_code) == password[self._password_index]:
            self._password_index += 1
            if self._password_index >= len(password):
                self._locked = False
                self._password_index = 0
                return False, True  # Block this key but unlock
        else:
            self._password_index = 0

        return False, False

    @property
    def is_locked(self) -> bool:
        """Return whether keyboard is locked."""
        return self._locked

    @property
    def should_show_message(self) -> bool:
        """Return whether to show the intrusion message."""
        if self._show_message:
            self._show_message = False
            return True
        return False


class NormalPolicy(Policy):
    """Block keystrokes during detected attack, resume when attack stops."""

    def on_intrusion(self, window_name: str, key: str, ascii_code: int) -> bool:
        """Log and block the keystroke."""
        self.log_event(window_name, key, ascii_code)
        return False

    def on_locked_keystroke(self, key: str, ascii_code: int) -> tuple[bool, bool]:
        """Normal policy doesn't lock, always allow."""
        return True, True


class SneakyPolicy(Policy):
    """Drop occasional keystrokes to break attack without being obvious."""

    def __init__(self, config: Config) -> None:
        """Initialize sneaky policy."""
        super().__init__(config)
        self._drop_counter = 0

    def on_intrusion(self, window_name: str, key: str, ascii_code: int) -> bool:
        """Drop every Nth keystroke."""
        self._drop_counter += 1
        if self._drop_counter >= self.config.randdrop:
            self._drop_counter = 0
            return False
        return True

    def on_locked_keystroke(self, key: str, ascii_code: int) -> tuple[bool, bool]:
        """Sneaky policy doesn't lock, always allow."""
        return True, True


class LogOnlyPolicy(Policy):
    """Log attacks but don't block any keystrokes."""

    def on_intrusion(self, window_name: str, key: str, ascii_code: int) -> bool:
        """Log the keystroke but allow it through."""
        self.log_event(window_name, key, ascii_code)
        return True

    def on_locked_keystroke(self, key: str, ascii_code: int) -> tuple[bool, bool]:
        """Log-only policy doesn't lock, always allow."""
        return True, True


def create_policy(config: Config) -> Policy:
    """Create the appropriate policy based on configuration.

    Args:
        config: DuckHunt configuration.

    Returns:
        Policy instance matching the configured policy type.
    """
    from duckhunt.config import Policy as PolicyEnum

    policies = {
        PolicyEnum.PARANOID: ParanoidPolicy,
        PolicyEnum.NORMAL: NormalPolicy,
        PolicyEnum.SNEAKY: SneakyPolicy,
        PolicyEnum.LOG: LogOnlyPolicy,
    }

    policy_class = policies.get(config.policy, NormalPolicy)
    return policy_class(config)
