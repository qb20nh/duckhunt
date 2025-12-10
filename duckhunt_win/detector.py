"""Keystroke detection logic."""

from __future__ import annotations

import collections
import time
from typing import Deque

class KeystrokeDetector:
    """Detects suspicious keystroke patterns."""

    def __init__(self, threshold_ms: int = 30, history_size: int = 25, 
                 burst_keys: int = 10, burst_window_ms: int = 100,
                 allow_auto_type: bool = True):
        """Initialize detector.

        Args:
            threshold_ms: Average interval threshold in ms (lower = suspicious).
            history_size: Number of keystrokes to keep in history.
            burst_keys: Number of keys to trigger burst detection.
            burst_window_ms: Time window for burst detection in ms.
            allow_auto_type: Whether to allow software-injected keys (placeholder for now).
        """
        self.threshold_ms = threshold_ms
        self.history_size = history_size
        self.burst_keys = burst_keys
        self.burst_window_ms = burst_window_ms
        self.allow_auto_type = allow_auto_type
        
        # Stores timestamps of recent keystrokes
        self._timestamps: Deque[float] = collections.deque(maxlen=history_size)

    def update_settings(self, threshold_ms: int, history_size: int, 
                        burst_keys: int, burst_window_ms: int,
                        allow_auto_type: bool) -> None:
        """Update detection settings at runtime."""
        self.threshold_ms = threshold_ms
        self.burst_keys = burst_keys
        self.burst_window_ms = burst_window_ms
        self.allow_auto_type = allow_auto_type
        
        # Resize history if needed
        if history_size != self.history_size:
            self.history_size = history_size
            # Create new deque with new size but keep existing items
            new_deque: Deque[float] = collections.deque(self._timestamps, maxlen=history_size)
            self._timestamps = new_deque

    def process_keystroke(self, timestamp: float | None = None) -> bool:
        """Process a keystroke and return True if suspicious.
        
        Args:
            timestamp: Time of keystroke (defaults to current time).
        """
        if timestamp is None:
            timestamp = time.time() * 1000  # Convert to ms
            
        self._timestamps.append(timestamp)
        
        return self._check_speed() or self._check_burst()

    def _check_speed(self) -> bool:
        """Check if average typing speed is suspiciously fast."""
        if len(self._timestamps) < self.history_size:
            return False
            
        # Calculate average interval between keys
        # We need at least 2 keys to have an interval
        total_time = self._timestamps[-1] - self._timestamps[0]
        avg_interval = total_time / (len(self._timestamps) - 1)
        
        return avg_interval < self.threshold_ms

    def _check_burst(self) -> bool:
        """Check for inhuman burst speeds."""
        if len(self._timestamps) < self.burst_keys:
            return False
            
        # Check time taken for the last N keys
        # Get the Nth most recent timestamp (index -N)
        # e.g. if burst_keys=10, we look at window from -10 to -1
        burst_start_time = self._timestamps[-self.burst_keys]
        burst_end_time = self._timestamps[-1]
        
        burst_duration = burst_end_time - burst_start_time
        
        return burst_duration < self.burst_window_ms

    def reset(self) -> None:
        """Reset detection history."""
        self._timestamps.clear()
