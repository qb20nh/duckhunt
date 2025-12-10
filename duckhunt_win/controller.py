"""
Main Application Controller.
Orchestrates View, IPC, Daemon, and Session Monitoring.
"""

from __future__ import annotations

import ctypes
import os
import queue
import secrets
import subprocess
import sys
import threading
import tkinter as tk
import winreg
from multiprocessing.connection import Listener
from pathlib import Path
from typing import Any

from duckhunt_win.config import Config
from duckhunt_win.core.session_monitor import SessionMonitor
from duckhunt_win.gui.settings import SettingsWindow
from duckhunt_win.gui.tray import DuckHuntTrayIcon
from duckhunt_win.ipc import (
    MSG_CONFIG,
    MSG_EXIT,
    MSG_START,
    MSG_STATUS,
    MSG_STOP,
    MSG_DETECTED,
    IPCMessage,
    get_ipc_address,
    get_window_ipc_address,
)


class DuckHuntController:
    """Main controller for DuckHunt application."""

    def __init__(self) -> None:
        # IPC Setup
        self.auth_key = secrets.token_bytes(32)
        os.environ["DUCKHUNT_AUTH_KEY"] = self.auth_key.hex()
        
        self.listener: Listener | None = None
        self.window_listener: Listener | None = None
        self.client_conn: Any = None
        self.daemon_process: subprocess.Popen[bytes] | None = None

        self.config = Config.load()
        self.daemon_status = "stopped"
        
        # State managed by event logic
        self.is_locked = False
        self.incident_pending = False

        # GUI Components
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Note: Tray Icon runs in separate thread, needs thread-safe calls
        self.tray = DuckHuntTrayIcon(
            on_start=self.on_start_request,
            on_stop=self.on_stop_request,
            on_settings=self.on_settings_request,
            on_exit=self.on_exit_request,
        )
        
        self.settings_window: SettingsWindow | None = None
        
        # Queue for cross-thread Tkinter updates
        self.gui_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        
        # Registers AUMID for persistence
        self._register_aumid()

        # Session Monitor (Event-Based)
        self.session_monitor = SessionMonitor(
            on_lock=self.on_session_lock,
            on_unlock=self.on_session_unlock
        )

    def _register_aumid(self) -> None:
        try:
            myappid = "DuckHunt"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    def start(self) -> None:
        """Start the application."""
        # 1. Start Session Monitor
        self.session_monitor.start()
        
        # 2. Start IPC Server
        self.start_ipc_server()
        
        # 3. Start Window IPC Server (Single Instance)
        self.start_window_ipc_server()
        
        # 4. Launch Daemon
        self.launch_daemon()

        # 5. Start auto-start retries (for daemon connection)
        threading.Thread(target=self._auto_start_monitor, daemon=True).start()

        # 6. Start Tray Icon (in background thread)
        threading.Thread(target=self.tray.start, daemon=True).start()

        # 7. Start GUI processing loop
        self.process_gui_queue()
        
        # 8. Enter Tkinter Mainloop
        self.root.mainloop()

    def process_gui_queue(self) -> None:
        """Process GUI updates in main thread."""
        try:
            while True:
                callback = self.gui_queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.process_gui_queue)

    def on_session_lock(self) -> None:
        """Called when workstation locks."""
        self.is_locked = True
        # If we have a pending incident, we note that the lock actually happened
        # No GUI action needed here usually

    def on_session_unlock(self) -> None:
        """Called when workstation unlocks."""
        self.is_locked = False
        if self.incident_pending:
            # User is back! Show notification safely on main thread
            self.gui_queue.put(lambda: self.tray.show_notification(
                "Attack Detected!", 
                "Workstation was locked to protect your system."
            ))
            self.incident_pending = False

    def on_start_request(self) -> None:
        self.send_command(MSG_START)

    def on_stop_request(self) -> None:
        self.send_command(MSG_STOP)

    def on_settings_request(self) -> None:
        # Must run on main thread
        self.gui_queue.put(self._open_settings)

    def _open_settings(self) -> None:
        if not self.settings_window:
            self.settings_window = SettingsWindow(self, self.root, self.config)
        self.settings_window.show()
        # Force lift/focus
        try:
            self.settings_window.window.lift()
            self.settings_window.window.focus_force()
        except Exception:
            pass

    def on_exit_request(self) -> None:
        self.gui_queue.put(self._shutdown)

    def _shutdown(self) -> None:
        self.send_command(MSG_EXIT)
        if self.daemon_process:
            self.daemon_process.terminate()
        
        self.session_monitor.stop()
        self.tray.stop()
        
        if self.listener:
            try:
                self.listener.close()
            except Exception:
                pass

        if self.window_listener:
            try:
                self.window_listener.close()
            except Exception:
                pass

        self.root.quit()

    def start_ipc_server(self) -> None:
        try:
            address = get_ipc_address()
            self.listener = Listener(address, authkey=self.auth_key)
        except Exception:
            return

        def accept_loop() -> None:
            if not self.listener:
                return
            while True:
                try:
                    conn = self.listener.accept()
                    self.client_conn = conn
                    self.handle_client(conn)
                except Exception:
                    break

        threading.Thread(target=accept_loop, daemon=True).start()

    def start_window_ipc_server(self) -> None:
        """Start IPC server for single-instance enforcement."""
        try:
            address = get_window_ipc_address()
            # No auth key needed for this simple signal check, or use same one?
            # It's better to use no auth key or a known static one because the client 
            # (new instance) won't know the random auth key of the server.
            # Using None for authkey means no authentication.
            self.window_listener = Listener(address, authkey=None)
        except Exception:
            # If we fail to bind, maybe another instance is running? 
            # But main check should handle that. If we are here, we passed main check.
            # Just ignore if fails, worst case single instance check doesn't work.
            return

        def window_accept_loop() -> None:
            if not self.window_listener:
                return
            while True:
                try:
                    conn = self.window_listener.accept()
                    self.handle_window_client(conn)
                except Exception:
                    break
        
        threading.Thread(target=window_accept_loop, daemon=True).start()

    def handle_window_client(self, conn: Any) -> None:
        try:
            # We just need to accept the connection to confirm existence.
            # No message is exchanged.
            pass 
        except Exception:
            pass
        finally:
            conn.close()

    def handle_client(self, conn: Any) -> None:
        while True:
            try:
                msg = conn.recv()
            except EOFError:
                break
            except Exception:
                break

            if isinstance(msg, IPCMessage):
                if msg.type == MSG_STATUS:
                    self._handle_status(msg)
                elif msg.type == MSG_DETECTED:
                    self._handle_detected()
        
        if self.client_conn == conn:
            self.client_conn = None

    def _handle_status(self, msg: IPCMessage) -> None:
        new_status = msg.payload.get("status", "unknown") if msg.payload else "unknown"
        old_status = self.daemon_status
        self.daemon_status = new_status
        
        if old_status != new_status:
            if new_status == "running":
                self.gui_queue.put(lambda: self.tray.show_notification(
                    "Protection Enabled", 
                    "DuckHunt is now monitoring keystroke patterns."
                ))
            elif new_status == "stopped":
                self.gui_queue.put(lambda: self.tray.show_notification(
                    "Protection Disabled", 
                    "DuckHunt monitoring is stopped."
                ))

        # Update Tray Menu
        is_running = (new_status == "running")
        self.tray.set_running_state(is_running)

    def _handle_detected(self) -> None:
        """Handle attack detection."""
        self.incident_pending = True
        # We don't need to poll "is_locked". 
        # We just wait for on_session_unlock event now.
        # Efficient!

    def send_command(self, type: str, payload: dict[str, Any] | None = None) -> None:
        if self.client_conn:
            msg = IPCMessage(type, payload)
            try:
                self.client_conn.send(msg)
            except Exception:
                self.client_conn = None

    def launch_daemon(self) -> None:
        if self.daemon_process and self.daemon_process.poll() is None:
            return

        env = os.environ.copy()
        
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            cmd = [sys.executable, "--daemon"]
        else:
            # Running as script
            cmd = [sys.executable, "-m", "duckhunt_win.daemon"]

        self.daemon_process = subprocess.Popen(
            cmd,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

    def _auto_start_monitor(self) -> None:
         import time
         for i in range(50):
             if self.client_conn:
                 self.send_command(MSG_START)
                 break
             time.sleep(0.1)

    def check_startup(self) -> bool:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                str(Path(r"Software\Microsoft\Windows\CurrentVersion\Run")),
                0,
                winreg.KEY_READ,
            )
            winreg.QueryValueEx(key, "DuckHunt")
            winreg.CloseKey(key)
            return True
        except WindowsError:
            return False

    def toggle_startup(self, enable: bool) -> None:
        key_path = str(Path(r"Software\Microsoft\Windows\CurrentVersion\Run"))
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS
            )
            if enable:
                exe = sys.executable
                cmd = f'"{exe}" -m duckhunt_win'
                winreg.SetValueEx(key, "DuckHunt", 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, "DuckHunt")
                except WindowsError:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass
