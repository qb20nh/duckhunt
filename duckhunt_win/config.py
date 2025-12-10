"""Configuration management for DuckHunt."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self


@dataclass(frozen=True, slots=True)
class Config:
    """DuckHunt configuration settings.

    Attributes:
        threshold: Avg keystroke interval threshold in ms (lower = suspicious).
        history_size: Number of keystrokes to keep in history.
        burst_keys: Number of keys to trigger burst detection.
        burst_window_ms: Time window for burst detection in ms.
        allow_auto_type: Allow software-injected keystrokes (e.g., KeePass).
    """

    threshold: int = 30
    history_size: int = 25
    burst_keys: int = 10
    burst_window_ms: int = 100
    allow_auto_type: bool = True
    run_on_startup: bool = True
    watchdog_enabled: bool = True


    @classmethod
    def from_legacy_conf(cls, path: Path) -> Self:
        """Load configuration from legacy duckhunt.conf Python file."""
        config_globals: dict[str, object] = {}
        try:
            exec(path.read_text(encoding="utf-8"), config_globals)  # noqa: S102
        except Exception:
            return cls()

        # Extract numeric values with type guards
        threshold_val = config_globals.get("threshold", 30)
        threshold = threshold_val if isinstance(threshold_val, int) else 30

        size_val = config_globals.get("history_size", 25)
        history_size = size_val if isinstance(size_val, int) else 25

        # New params not in legacy conf, use defaults
        burst_keys = 10
        burst_window_ms = 100

        return cls(
            threshold=threshold,
            history_size=history_size,
            burst_keys=burst_keys,
            burst_window_ms=burst_window_ms,
            allow_auto_type=bool(config_globals.get("allow_auto_type_software", True)),
            run_on_startup=bool(config_globals.get("run_on_startup", True)),
            watchdog_enabled=bool(config_globals.get("watchdog_enabled", True)),
        )

    @classmethod
    def from_toml(cls, path: Path) -> Self:
        """Load configuration from TOML file."""
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return cls()
            
        duckhunt = data.get("duckhunt", {})

        return cls(
            threshold=duckhunt.get("threshold", 30),
            history_size=duckhunt.get("history_size", 25),
            burst_keys=duckhunt.get("burst_keys", 10),
            burst_window_ms=duckhunt.get("burst_window_ms", 100),
            allow_auto_type=duckhunt.get("allow_auto_type", True),
            run_on_startup=duckhunt.get("run_on_startup", True),
            watchdog_enabled=duckhunt.get("watchdog_enabled", True),
        )

    @classmethod
    def load(cls, config_path: Path | None = None) -> Self:
        """Load configuration from file, auto-detecting format.
        
        Priority:
        1. Explicit path
        2. duckhunt.conf in CWD
        3. duckhunt.conf in User Home
        4. Embedded default
        """
        if config_path is not None and config_path.exists():
            if config_path.suffix == ".toml":
                return cls.from_toml(config_path)
            return cls.from_legacy_conf(config_path)

        # Search paths
        cwd = Path.cwd()
        home = Path.home()
        
        paths = [
            cwd / "duckhunt.toml",
            cwd / "duckhunt.conf",
            home / "duckhunt.conf",
        ]
        
        for path in paths:
            if path.exists():
                if path.suffix == ".toml":
                    return cls.from_toml(path)
                return cls.from_legacy_conf(path)

        # Return defaults (embedded loading logic simplified to defaults for now 
        # as class params match the default conf)
        return cls()
