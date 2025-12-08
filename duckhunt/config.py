"""Configuration management for DuckHunt."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Self


class Policy(Enum):
    """Protection policy types."""

    PARANOID = "paranoid"
    NORMAL = "normal"
    SNEAKY = "sneaky"
    LOG = "log"


@dataclass(frozen=True, slots=True)
class Config:
    """DuckHunt configuration settings.

    Attributes:
        policy: Protection policy to use when attack is detected.
        password: Password to unlock keyboard in paranoid mode.
        blacklist: List of window names to always treat as suspicious.
        threshold: Keystroke speed threshold in milliseconds.
        history_size: Number of keystrokes to track for speed averaging.
        randdrop: How often to drop a keystroke in sneaky mode.
        log_filename: File to log detected attacks.
        allow_auto_type: Allow software-injected keystrokes (e.g., KeePass).
    """

    policy: Policy = Policy.NORMAL
    password: str = "quack"
    blacklist: list[str] = field(default_factory=lambda: ["Command Prompt", "Windows PowerShell"])
    threshold: int = 30
    history_size: int = 25
    randdrop: int = 6
    log_filename: str = "log.txt"
    allow_auto_type: bool = True

    @classmethod
    def from_legacy_conf(cls, path: Path) -> Self:
        """Load configuration from legacy duckhunt.conf Python file.

        Args:
            path: Path to the duckhunt.conf file.

        Returns:
            Config instance with loaded settings.
        """
        config_globals: dict[str, object] = {}
        exec(path.read_text(encoding="utf-8"), config_globals)  # noqa: S102

        blacklist_str = config_globals.get("blacklist", "Command Prompt, Windows PowerShell")
        if isinstance(blacklist_str, str):
            blacklist = [item.strip() for item in blacklist_str.split(",")]
        elif isinstance(blacklist_str, (list, tuple)):
            blacklist = [str(item) for item in blacklist_str]
        else:
            blacklist = []

        policy_str = str(config_globals.get("policy", "normal")).lower()
        try:
            policy = Policy(policy_str)
        except ValueError:
            policy = Policy.NORMAL

        # Extract numeric values with type guards
        threshold_val = config_globals.get("threshold", 30)
        threshold = threshold_val if isinstance(threshold_val, int) else 30

        size_val = config_globals.get("size", 25)
        history_size = size_val if isinstance(size_val, int) else 25

        randdrop_val = config_globals.get("randdrop", 6)
        randdrop = randdrop_val if isinstance(randdrop_val, int) else 6

        return cls(
            policy=policy,
            password=str(config_globals.get("password", "quack")),
            blacklist=blacklist,
            threshold=threshold,
            history_size=history_size,
            randdrop=randdrop,
            log_filename=str(config_globals.get("filename", "log.txt")),
            allow_auto_type=bool(config_globals.get("allow_auto_type_software", True)),
        )

    @classmethod
    def from_toml(cls, path: Path) -> Self:
        """Load configuration from TOML file.

        Args:
            path: Path to the TOML configuration file.

        Returns:
            Config instance with loaded settings.
        """
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        duckhunt = data.get("duckhunt", {})

        policy_str = str(duckhunt.get("policy", "normal")).lower()
        try:
            policy = Policy(policy_str)
        except ValueError:
            policy = Policy.NORMAL

        return cls(
            policy=policy,
            password=duckhunt.get("password", "quack"),
            blacklist=duckhunt.get("blacklist", ["Command Prompt", "Windows PowerShell"]),
            threshold=duckhunt.get("threshold", 30),
            history_size=duckhunt.get("history_size", 25),
            randdrop=duckhunt.get("randdrop", 6),
            log_filename=duckhunt.get("log_filename", "log.txt"),
            allow_auto_type=duckhunt.get("allow_auto_type", True),
        )

    @classmethod
    def load(cls, config_path: Path | None = None) -> Self:
        """Load configuration from file, auto-detecting format.

        Args:
            config_path: Optional path to config file. If None, searches for
                duckhunt.toml or duckhunt.conf in the current directory.

        Returns:
            Config instance with loaded settings.
        """
        if config_path is not None:
            if config_path.suffix == ".toml":
                return cls.from_toml(config_path)
            return cls.from_legacy_conf(config_path)

        # Search for config files
        cwd = Path.cwd()
        toml_path = cwd / "duckhunt.toml"
        if toml_path.exists():
            return cls.from_toml(toml_path)

        conf_path = cwd / "duckhunt.conf"
        if conf_path.exists():
            return cls.from_legacy_conf(conf_path)

        # Check package resources for default config
        resources_path = Path(__file__).parent / "resources" / "duckhunt.default.conf"
        if resources_path.exists():
            return cls.from_legacy_conf(resources_path)

        # Return defaults
        return cls()
