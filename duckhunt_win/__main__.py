
"""DuckHunt entry point."""

from __future__ import annotations

import sys
import ctypes
from multiprocessing.connection import Client

from duckhunt_win.controller import DuckHuntController
from duckhunt_win.ipc import get_window_ipc_address

def main() -> int:
    """Run the DuckHunt tray application."""
    if "--daemon" in sys.argv:
        from duckhunt_win.daemon import DuckHuntDaemon
        daemon = DuckHuntDaemon()
        daemon.run()
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
        app = DuckHuntController()
        app.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
