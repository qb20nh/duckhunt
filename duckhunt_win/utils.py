"""
Utility functions for DuckHunt.
"""
from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    
    Args:
        relative_path: Relative path to resource (e.g. "resources/icon.ico")
        
    Returns:
        Path object pointing to the resource.
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
        # Check if resource is directly at root (build script: dest=".")
        if (base_path / relative_path).exists():
            return base_path / relative_path
        # Check if resource is under package name (build script: dest="duckhunt_win/...")
        # This handles the current build.py configuration
        elif (base_path / "duckhunt_win" / relative_path).exists():
            return base_path / "duckhunt_win" / relative_path
        
        return base_path / relative_path
    else:
        # running in normal python environment
        # Currently assuming utils.py is in duckhunt_win/
        base_path = Path(__file__).parent
        
    return base_path / relative_path

# Input Injection Detection
# LLKHF_INJECTED = 0x00000010
LLKHF_INJECTED = 0x10

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_ulong),
        ("scanCode", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]



# Process Utilities
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
SYNCHRONIZE = 0x00100000

def is_pid_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    if pid <= 0:
        return False
    
    try:
        # Open the process with specific rights
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | SYNCHRONIZE, 
            False, 
            pid
        )
        if not handle:
            return False

        # Check exit code
        exit_code = ctypes.c_ulong()
        if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
             # STILL_ACTIVE = 259
            is_running = (exit_code.value == 259)
            ctypes.windll.kernel32.CloseHandle(handle)
            return is_running
        
        ctypes.windll.kernel32.CloseHandle(handle)
        return False
    except Exception:
        return False
