"""
Watchdog process for DuckHunt.
Monitors the Controller and Daemon processes, ensuring they remain active.
"""

from __future__ import annotations

import argparse
import ctypes
import os
import subprocess
import sys
import time
import winreg
from pathlib import Path
from typing import NoReturn

from duckhunt_win.utils import is_pid_running


class Watchdog:
    """Supervisor for DuckHunt processes."""

    def __init__(self, parent_pid: int, auth_key: str) -> None:
        self.parent_pid = parent_pid
        self.auth_key = auth_key
        # We assume responsibility for launching/restarting the daemon
        self.daemon_process: subprocess.Popen[bytes] | None = None
        self.controller_process_pid: int | None = parent_pid
        
        # State
        self.should_exit = False

    def launch_daemon(self) -> None:
        """Launch the Daemon process."""
        env = os.environ.copy()
        env["DUCKHUNT_AUTH_KEY"] = self.auth_key # Ensure it has the key
        
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, "--daemon"]
        else:
            cmd = [sys.executable, "-m", "duckhunt_win.daemon"]

        self.daemon_process = subprocess.Popen(
            cmd,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

    def launch_controller(self) -> None:
        """Relaunch the Controller (GUI) process."""
        # Relaunch controller with the same Auth Key and our Watchdog PID
        # so it knows it is being monitored.
        env = os.environ.copy()
        
        cmd = []
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, "--auth-key", self.auth_key, "--watchdog-pid", str(os.getpid())]
        else:
            cmd = [sys.executable, "-m", "duckhunt_win", "--auth-key", self.auth_key, "--watchdog-pid", str(os.getpid())]
            
        proc = subprocess.Popen(cmd, env=env)
        self.controller_process_pid = proc.pid

    def run(self) -> None:
        """Main loop."""
        
        # 1. Start Daemon immediately
        self.launch_daemon()
        
        while not self.should_exit:
            time.sleep(1.0)
            
            # Check Daemon
            if self.daemon_process:
                if self.daemon_process.poll() is not None:
                    print("Watchdog: Daemon died. Restarting...")
                    self.launch_daemon()
            else:
                 self.launch_daemon()
            
            # Check Controller
            if self.controller_process_pid:
                if not is_pid_running(self.controller_process_pid):
                    print("Watchdog: Controller died. Restarting...")
                    self.launch_controller()
            else:
                self.launch_controller()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-pid", type=int, required=True, help="PID of the Controller process")
    parser.add_argument("--auth-key", type=str, required=True, help="Hex encoded Auth Key")
    
    args = parser.parse_args()
    
    watchdog = Watchdog(parent_pid=args.parent_pid, auth_key=args.auth_key)
    watchdog.run()
    return 0

if __name__ == "__main__":
    sys.exit(main())
