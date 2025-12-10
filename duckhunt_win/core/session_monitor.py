"""
Windows Session Monitor using native Win32 APIs.
Detects Lock/Unlock events without polling.
"""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable, Optional

# Constants
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
NOTIFY_FOR_THIS_SESSION = 0

# ctypes definitions
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
wtsapi32 = ctypes.windll.wtsapi32

# Check for 64-bit to use correct pointer size types
if ctypes.sizeof(ctypes.c_void_p) == 8:
    LRESULT = ctypes.c_int64
else:
    LRESULT = ctypes.c_long

WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ('style', wintypes.UINT),
        ('lpfnWndProc', WNDPROC),
        ('cbClsExtra', ctypes.c_int),
        ('cbWndExtra', ctypes.c_int),
        ('hInstance', wintypes.HINSTANCE),
        ('hIcon', wintypes.HICON),
        ('hCursor', wintypes.HANDLE),
        ('hbrBackground', wintypes.HBRUSH),
        ('lpszMenuName', wintypes.LPCWSTR),
        ('lpszClassName', wintypes.LPCWSTR),
    ]


class SessionMonitor:
    """Monitors Windows Session events (Lock/Unlock)."""

    def __init__(self, on_lock: Callable[[], None], on_unlock: Callable[[], None]) -> None:
        self.on_lock = on_lock
        self.on_unlock = on_unlock
        self.hwnd: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """Start the monitor thread."""
        if self._thread:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the monitor (best effort, as GetMessage blocks)."""
        self._running = False
        if self.hwnd:
            user32.PostMessageW(self.hwnd, 0x0010, 0, 0) # WM_CLOSE

    def _run(self) -> None:
        """Message loop thread."""
        hInstance = kernel32.GetModuleHandleW(None)
        class_name = "DuckHuntSessionMonitor"

        def wnd_proc(hwnd: int, msg: int, wParam: int, lParam: int) -> int:
            if msg == WM_WTSSESSION_CHANGE:
                if wParam == WTS_SESSION_LOCK:
                    self.on_lock()
                elif wParam == WTS_SESSION_UNLOCK:
                    self.on_unlock()
            elif msg == 0x0010: # WM_CLOSE
                 user32.PostQuitMessage(0)
                 return 0
            return user32.DefWindowProcW(hwnd, msg, wParam, lParam)

        wnd_class = WNDCLASS()
        wnd_class.lpfnWndProc = WNDPROC(wnd_proc)
        wnd_class.hInstance = hInstance
        wnd_class.lpszClassName = class_name

        if not user32.RegisterClassW(ctypes.byref(wnd_class)):
             # Class might already be registered
             pass

        self.hwnd = user32.CreateWindowExW(
            0,
            class_name,
            "DuckHunt Hidden Monitor",
            0,
            0, 0, 0, 0,
            0,
            0,
            hInstance,
            None
        )

        if not self.hwnd:
            return

        # Register for session notifications
        if not wtsapi32.WTSRegisterSessionNotification(self.hwnd, NOTIFY_FOR_THIS_SESSION):
             pass

        # Message pump
        msg = wintypes.MSG()
        while self._running:
            bRet = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if bRet == 0 or bRet == -1:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        wtsapi32.WTSUnRegisterSessionNotification(self.hwnd)
        user32.DestroyWindow(self.hwnd)
        user32.UnregisterClassW(class_name, hInstance)
