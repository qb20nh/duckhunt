"""Keystroke detection engine."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from duckhunt.config import Config
    from duckhunt.policies import Policy


class KeystrokeDetector:
    """Detects suspicious keystroke injection attacks.

    Uses a circular buffer to track keystroke timing and detect
    abnormally fast typing that indicates automated injection.
    """

    def __init__(
        self,
        config: Config,
        policy: Policy,
        on_intrusion: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize the detector.

        Args:
            config: DuckHunt configuration.
            policy: Protection policy to apply.
            on_intrusion: Optional callback when intrusion is detected.
        """
        self.config = config
        self.policy = policy
        self._on_intrusion = on_intrusion

        # Circular buffer for keystroke timing
        self._history: deque[int] = deque(
            [config.threshold + 1] * config.history_size,
            maxlen=config.history_size,
        )
        self._prev_time: int = -1
        self._intrusion_active: bool = False

    @property
    def average_speed(self) -> float:
        """Current average keystroke speed in milliseconds."""
        if not self._history:
            return float("inf")
        return sum(self._history) / len(self._history)

    @property
    def is_intrusion_active(self) -> bool:
        """Whether an intrusion is currently detected."""
        return self._intrusion_active

    def process_keystroke(
        self,
        key: str,
        ascii_code: int,
        timestamp: int,
        window_name: str,
        is_injected: bool,
    ) -> bool:
        """Process a keystroke event.

        Args:
            key: Key name (e.g., 'A', 'Return').
            ascii_code: ASCII code of the key.
            timestamp: Timestamp of the keystroke in milliseconds.
            window_name: Name of the active window.
            is_injected: Whether the keystroke was software-injected.

        Returns:
            True to allow the keystroke, False to block it.
        """
        # Allow software-injected keystrokes if configured
        if is_injected and self.config.allow_auto_type:
            return True

        # Handle locked state (paranoid mode)
        if self._intrusion_active and hasattr(self.policy, "is_locked"):
            from duckhunt.policies import ParanoidPolicy

            if isinstance(self.policy, ParanoidPolicy) and self.policy.is_locked:
                allow, unlocked = self.policy.on_locked_keystroke(key, ascii_code)
                if unlocked:
                    self._intrusion_active = False
                return allow

        # Initial keystroke - no timing data yet
        if self._prev_time == -1:
            self._prev_time = timestamp
            return True

        # Calculate and record keystroke interval
        interval = timestamp - self._prev_time
        self._prev_time = timestamp
        self._history.append(interval)

        # Check blacklisted windows
        for blacklisted in self.config.blacklist:
            if blacklisted in window_name:
                return self._handle_intrusion(window_name, key, ascii_code)

        # Check speed threshold
        if self.average_speed < self.config.threshold:
            return self._handle_intrusion(window_name, key, ascii_code)

        # No intrusion - reset state
        self._intrusion_active = False
        return True

    def _handle_intrusion(self, window_name: str, key: str, ascii_code: int) -> bool:
        """Handle a detected intrusion.

        Args:
            window_name: Name of the active window.
            key: Key that triggered detection.
            ascii_code: ASCII code of the key.

        Returns:
            True to allow keystroke, False to block.
        """
        self._intrusion_active = True

        if self._on_intrusion:
            self._on_intrusion("Quack! Quack! -- Time to go Duckhunting!")

        return self.policy.on_intrusion(window_name, key, ascii_code)

    def reset(self) -> None:
        """Reset the detector state."""
        self._history.clear()
        self._history.extend([self.config.threshold + 1] * self.config.history_size)
        self._prev_time = -1
        self._intrusion_active = False
