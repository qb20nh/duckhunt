"""
System Tray Icon GUI (View).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pystray
from PIL import Image, ImageDraw

from duckhunt_win.utils import get_resource_path


class DuckHuntTrayIcon:
    """System tray icon view."""

    def __init__(
        self,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_settings: Callable[[], None],
        on_exit: Callable[[], None],
    ):
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_settings = on_settings
        self._on_exit = on_exit
        
        self.icon: pystray.Icon | None = None
        self.running_state = False  # Track visual state "Start/Stop"

    def set_running_state(self, is_running: bool) -> None:
        """Update the running state to toggle menu text."""
        self.running_state = is_running
        self.update_menu()

    def create_image(self) -> Image.Image:
        """Create a default icon image."""
        # Try load from resources
        icon_path = get_resource_path("resources/favicon.ico")
        if icon_path.exists():
            return Image.open(icon_path)

        # Fallback generated icon
        width = 64
        height = 64
        color1 = "black"
        color2 = "white"
        
        image = Image.new("RGB", (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
        dc.rectangle((0, height // 2, width // 2, height), fill=color2)
        return image

    def start(self) -> None:
        """Start the tray icon loop."""
        def get_state_label(item: Any) -> str:
            return "Stop Monitoring" if self.running_state else "Start Monitoring"

        def on_toggle_click(icon: Any, item: Any) -> None:
            if self.running_state:
                self._on_stop()
            else:
                self._on_start()

        menu = pystray.Menu(
            pystray.MenuItem(get_state_label, on_toggle_click),
            pystray.MenuItem("Settings", lambda: self._on_settings()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", lambda: self._on_exit())
        )

        self.icon = pystray.Icon(
            "DuckHunt",
            self.create_image(),
            "DuckHunt Protection",
            menu
        )
        self.icon.run()

    def stop(self) -> None:
        """Stop the tray icon."""
        if self.icon:
            self.icon.stop()

    def update_menu(self) -> None:
        """Force menu refresh."""
        if self.icon:
            self.icon.update_menu()

    def show_notification(self, title: str, message: str) -> None:
        """Show desktop notification."""
        if self.icon:
            self.icon.notify(message, title)
