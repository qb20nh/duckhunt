"""Inter-process communication for DuckHunt."""

from __future__ import annotations


from dataclasses import dataclass
from typing import Any

# Message Types
MSG_START = "start"
MSG_STOP = "stop"
MSG_STATUS = "status"
MSG_DETECTED = "detected"
MSG_CONFIG = "config"
MSG_EXIT = "exit"


def get_ipc_address() -> str:
    """Get the IPC address (Named Pipe on Windows)."""
    return r"\\.\pipe\duckhunt_ipc"


def get_window_ipc_address() -> str:
    """Get the IPC address for the window/single-instance check."""
    return r"\\.\pipe\duckhunt_window"


@dataclass
class IPCMessage:
    """Standard IPC message format."""

    type: str
    payload: dict[str, Any] | None = None
