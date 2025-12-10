"""Background daemon for monitoring keystrokes."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import sys
from multiprocessing.connection import Client
from typing import Any

from pynput import keyboard

from duckhunt_win.detector import KeystrokeDetector
from duckhunt_win.ipc import (
    MSG_DETECTED,
    MSG_EXIT,
    MSG_START,
    MSG_STATUS,
    MSG_STOP,
    MSG_CONFIG,
    IPCMessage,
    get_ipc_address,
)


class DuckHuntDaemon:
    """Daemon process that monitors keystrokes and locks workstation."""

    def __init__(self) -> None:
        self.detector = KeystrokeDetector()
        self.running = False
        self.conn: Any = None
        self._listener: keyboard.Listener | None = None
        
        # Get Auth Key from environment
        auth_key_hex = os.environ.get("DUCKHUNT_AUTH_KEY")
        if not auth_key_hex:
            # Cannot run without auth key
            sys.exit(1)
        self.auth_key = bytes.fromhex(auth_key_hex)

    def connect(self) -> None:
        """Connect to the GUI process."""
        try:
            address = get_ipc_address()
            self.conn = Client(address, authkey=self.auth_key)
            self.send_status("connected")
        except Exception:
            # GUI not running or auth failed
            sys.exit(1)

    def send_message(self, type: str, payload: dict[str, Any] | None = None) -> None:
        """Send message to GUI."""
        if self.conn:
            msg = IPCMessage(type, payload)
            try:
                self.conn.send(msg)
            except Exception:
                sys.exit(1)

    def send_status(self, status: str) -> None:
        """Send status update."""
        self.send_message(MSG_STATUS, {"status": status})

    def lock_workstation(self) -> None:
        """Lock the Windows workstation."""
        self.send_message(MSG_DETECTED, {"action": "locked"})
        ctypes.windll.user32.LockWorkStation()
        # Reset detection to avoid loop
        self.detector.reset()

    def on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        """Handle key press."""
        if not self.running:
            return

        is_suspicious = self.detector.process_keystroke()
        if is_suspicious:
            self.lock_workstation()

    def start_monitoring(self) -> None:
        """Start keyboard listener."""
        if not self._listener:
            self._listener = keyboard.Listener(on_press=self.on_press)
            self._listener.start()
        self.running = True
        self.send_status("running")

    def stop_monitoring(self) -> None:
        """Stop keyboard monitoring."""
        self.running = False
        self.detector.reset()
        self.send_status("stopped")

    def set_high_priority(self) -> None:
        """Set process priority to high for better responsiveness."""
        try:
            # Re-define for robustness
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            
            GetCurrentProcess = kernel32.GetCurrentProcess
            GetCurrentProcess.restype = wintypes.HANDLE
            
            SetPriorityClass = kernel32.SetPriorityClass
            SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            SetPriorityClass.restype = wintypes.BOOL
            
            HIGH_PRIORITY_CLASS = 0x00000080
            
            handle = GetCurrentProcess()
            if not SetPriorityClass(handle, HIGH_PRIORITY_CLASS):
                # Silently fail or log if possible
                pass
        except Exception:
            pass

    def run(self) -> None:
        """Main daemon loop."""
        self.set_high_priority()
        self.connect()

        # Listen for commands
        while True:
            try:
                msg = self.conn.recv()
            except EOFError:
                break
            except Exception:
                break

            if isinstance(msg, IPCMessage):
                if msg.type == MSG_START:
                    self.start_monitoring()
                elif msg.type == MSG_STOP:
                    self.stop_monitoring()
                elif msg.type == MSG_CONFIG:
                    if msg.payload:
                        self.detector.update_settings(
                            threshold_ms=msg.payload.get("threshold", 30),
                            history_size=msg.payload.get("history_size", 25),
                            burst_keys=msg.payload.get("burst_keys", 10),
                            burst_window_ms=msg.payload.get("burst_window_ms", 100),
                            allow_auto_type=msg.payload.get("allow_auto_type", True)
                        )
                elif msg.type == MSG_EXIT:
                    break

        if self._listener:
            self._listener.stop()
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    daemon = DuckHuntDaemon()
    daemon.run()
