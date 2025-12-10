import ctypes
from ctypes import wintypes
import os
import sys
import time
import atexit
from multiprocessing.connection import Client
from typing import Any

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

# Load user32 for hooks
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# WinAPI Constants
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
LLKHF_INJECTED = 0x00000010

# Hook Struct
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

# Callback type
CMPFUNC = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, ctypes.POINTER(KBDLLHOOKSTRUCT))


class DuckHuntDaemon:
    """Daemon process that monitors keystrokes and locks workstation."""

    def __init__(self) -> None:
        self.detector = KeystrokeDetector()
        self.running = False
        self.conn: Any = None
        self._hook_id = None
        self._hook_proc = None # Keep reference to avoid GC
        
        # Get Auth Key from environment
        auth_key_hex = os.environ.get("DUCKHUNT_AUTH_KEY")
        if not auth_key_hex:
            # Cannot run without auth key
            sys.exit(1)
        self.auth_key = bytes.fromhex(auth_key_hex)

    def connect(self) -> bool:
        """Connect to the GUI process."""
        try:
            address = get_ipc_address()
            self.conn = Client(address, authkey=self.auth_key)
            self.send_status("connected")
            return True
        except Exception:
            # GUI not running or wait
            return False

    def send_message(self, type: str, payload: dict[str, Any] | None = None) -> None:
        """Send message to GUI."""
        if self.conn:
            msg = IPCMessage(type, payload)
            try:
                self.conn.send(msg)
            except Exception:
                # Connection loss handled in run loop
                raise

    def send_status(self, status: str) -> None:
        """Send status update."""
        self.send_message(MSG_STATUS, {"status": status})

    def lock_workstation(self) -> None:
        """Lock the Windows workstation."""
        self.send_message(MSG_DETECTED, {"action": "locked"})
        user32.LockWorkStation()
        # Reset detection to avoid loop
        self.detector.reset()

    def _low_level_keyboard_proc(self, nCode, wParam, lParam):
        """Windows Hook Callback."""
        if nCode >= 0:
            if wParam == WM_KEYDOWN or wParam == WM_SYSKEYDOWN:
                if self.running:
                    kb_struct = lParam.contents
                    is_injected = bool(kb_struct.flags & LLKHF_INJECTED)
                    
                    # Detect
                    is_suspicious = self.detector.process_keystroke(is_injected=is_injected)
                    if is_suspicious:
                        self.lock_workstation()
        
        return user32.CallNextHookEx(self._hook_id, nCode, wParam, lParam)

    def start_monitoring(self) -> None:
        """Start keyboard listener (Install Hook)."""
        if not self._hook_id:
            self._hook_proc = CMPFUNC(self._low_level_keyboard_proc)
            self._hook_id = user32.SetWindowsHookExA(
                WH_KEYBOARD_LL, 
                self._hook_proc, 
                kernel32.GetModuleHandleW(None), 
                0
            )
            if not self._hook_id:
                 print(f"Failed to install hook: {ctypes.GetLastError()}", file=sys.stderr)
                 return

        self.running = True
        self.send_status("running")

    def stop_monitoring(self) -> None:
        """Stop keyboard monitoring (Uninstall Hook)."""
        self.running = False
        if self._hook_id:
            user32.UnhookWindowsHookEx(self._hook_id)
            self._hook_id = None
            self._hook_proc = None
            
        self.detector.reset()
        self.send_status("stopped")

    def set_high_priority(self) -> None:
        """Set process priority to high for better responsiveness."""
        try:
            GetCurrentProcess = kernel32.GetCurrentProcess
            GetCurrentProcess.restype = wintypes.HANDLE
            
            SetPriorityClass = kernel32.SetPriorityClass
            SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            SetPriorityClass.restype = wintypes.BOOL
            
            HIGH_PRIORITY_CLASS = 0x00000080
            
            handle = GetCurrentProcess()
            SetPriorityClass(handle, HIGH_PRIORITY_CLASS)
        except Exception:
            pass

    def run(self) -> None:
        """Main daemon loop."""
        self.set_high_priority()
        
        # Message Pump for Windows Hook
        msg = wintypes.MSG()
        
        while True:
            # Connection Loop
            while not self.conn:
                if self.connect():
                    break
                
                # We need to pump messages even while connecting? 
                # Hooks usually need a message loop on the thread that installed them.
                # But here we haven't installed hook yet (start_monitoring does).
                # Wait, if we installed hooks, we MUST pump.
                # If disconnected, we stop monitoring.
                time.sleep(1.0)
            
            # Application Loop with Message Pump
            while self.conn:
                # 1. Pump Windows Messages (Non-blocking)
                if user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1): # PM_REMOVE = 1
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                
                # 2. Check IPC Messages (Non-blocking polling)
                if self.conn and self.conn.poll(0.01): # 10ms poll
                    try:
                        msg_ipc = self.conn.recv()
                        if isinstance(msg_ipc, IPCMessage):
                            if msg_ipc.type == MSG_START:
                                self.start_monitoring()
                            elif msg_ipc.type == MSG_STOP:
                                self.stop_monitoring()
                            elif msg_ipc.type == MSG_CONFIG:
                                if msg_ipc.payload:
                                    self.detector.update_settings(
                                        threshold_ms=msg_ipc.payload.get("threshold", 30),
                                        history_size=msg_ipc.payload.get("history_size", 25),
                                        burst_keys=msg_ipc.payload.get("burst_keys", 10),
                                        burst_window_ms=msg_ipc.payload.get("burst_window_ms", 100),
                                        allow_auto_type=msg_ipc.payload.get("allow_auto_type", True)
                                    )
                            elif msg_ipc.type == MSG_EXIT:
                                self.stop_monitoring()
                                if self.conn:
                                    self.conn.close()
                                return
                    except (EOFError, Exception):
                        self.conn = None
                        self.stop_monitoring()
                        break
                
                # Small sleep to yield CPU? call_next_hook might delay if we sleep too much
                # PeekMessage logic usually is sufficient for CPU yielding if no msg
                # But poll(0.01) waits up to 10ms. This is fine.


if __name__ == "__main__":
    daemon = DuckHuntDaemon()
    try:
        daemon.run()
    except KeyboardInterrupt:
        pass
