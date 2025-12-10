
"""DuckHunt entry point."""

from __future__ import annotations

import sys
import ctypes
from multiprocessing.connection import Client

from duckhunt_win.controller import DuckHuntController
from duckhunt_win.ipc import get_window_ipc_address

def main() -> int:
    """Run the DuckHunt tray application."""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--watchdog", action="store_true", help="Run as watchdog")
    parser.add_argument("--auth-key", type=str, help="Hex encoded Auth Key")
    parser.add_argument("--parent-pid", type=int, help="Parent PID for watchdog")
    parser.add_argument("--watchdog-pid", type=int, help="Existing Watchdog PID")
    
    args, unknown = parser.parse_known_args()

    if args.daemon:
        from duckhunt_win.daemon import DuckHuntDaemon
        daemon = DuckHuntDaemon()
        daemon.run()
        return 0

    if args.watchdog:
        if not args.parent_pid or not args.auth_key:
             # Should not happen if invoked correctly
             return 1
        from duckhunt_win.watchdog import Watchdog
        wd = Watchdog(parent_pid=args.parent_pid, auth_key=args.auth_key)
        wd.run()
        return 0

    # Single Instance Check
    try:
        address = get_window_ipc_address()
        # access_token=None because we set authkey=None in the server
        with Client(address, authkey=None) as conn:
            # Just connect to check existence
            pass
        
        # If we reached here, another instance accepted our connection.
        print("DuckHunt is already running.")
        
        # Warn user
        ctypes.windll.user32.MessageBoxW(
            0, 
            "DuckHunt is already running.", 
            "DuckHunt Already Running", 
            0x30 | 0x0  # MB_ICONWARNING | MB_OK
        )
        return 0
    except (OSError, ValueError):
        # ValueError/OSError implies connection failed => instance not likely running
        pass

    try:
        app = DuckHuntController(auth_key_hex=args.auth_key, watchdog_pid=args.watchdog_pid)
        app.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
