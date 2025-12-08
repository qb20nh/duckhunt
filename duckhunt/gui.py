"""DuckHunt GUI application."""

from __future__ import annotations

import getpass
import os
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from duckhunt.config import Config
    from duckhunt.detector import KeystrokeDetector


class DuckHuntApp:
    """Main DuckHunt application window."""

    WINDOW_TITLE = "DuckHunter"
    WINDOW_SIZE = "310x45"
    ABOUT_URL = "https://github.com/pmsosa/duckhunt/blob/master/README.md"

    def __init__(self, config: Config, detector: KeystrokeDetector) -> None:
        """Initialize the application.

        Args:
            config: DuckHunt configuration.
            detector: Keystroke detector instance.
        """
        self.config = config
        self.detector = detector
        self._hook_manager: object | None = None
        self._running = False

        self._root = tk.Tk()
        self._setup_window(self._root)
        self._create_menu(self._root, is_main=True)
        self._create_buttons(self._root, is_main=True)

    def _setup_window(self, window: tk.Tk | tk.Toplevel) -> None:
        """Configure window properties.

        Args:
            window: Window to configure.
        """
        window.title(self.WINDOW_TITLE)

        # Set icon if available
        icon_path = Path(__file__).parent / "resources" / "favicon.ico"
        if icon_path.exists():
            try:
                window.iconbitmap(str(icon_path))
            except tk.TclError:
                pass  # Icon format not supported

        window.geometry(self.WINDOW_SIZE)
        window.resizable(False, False)
        window.geometry("+300+300")
        window.attributes("-topmost", True)

    def _create_menu(self, window: tk.Tk | tk.Toplevel, *, is_main: bool) -> None:
        """Create the menu bar.

        Args:
            window: Window to add menu to.
            is_main: True if this is the main (pre-start) window.
        """
        menubar = tk.Menu(window)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        if is_main:
            file_menu.add_command(label="START", command=self._start_monitoring)
            file_menu.add_command(label="CLOSE", command=self._stop)
        else:
            file_menu.add_command(label="STOP SCRIPT", command=self._stop)
            file_menu.add_command(label="CLOSE WINDOW", command=window.destroy)
        file_menu.add_separator()
        file_menu.add_command(label="ABOUT", command=self._show_about)
        menubar.add_cascade(label="Menu", menu=file_menu)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="RUN ON STARTUP", command=self._add_to_startup)
        settings_menu.add_command(
            label="FULLSCREEN", command=lambda: self._toggle_fullscreen(window)
        )
        settings_menu.add_command(
            label="HIDE TITLE BAR", command=lambda: window.overrideredirect(True)
        )
        menubar.add_cascade(label="Settings", menu=settings_menu)

        window.config(menu=menubar)

    def _create_buttons(self, window: tk.Tk | tk.Toplevel, *, is_main: bool) -> None:
        """Create the button bar.

        Args:
            window: Window to add buttons to.
            is_main: True if this is the main (pre-start) window.
        """
        if is_main:
            start_btn = ttk.Button(window, text="Start", command=self._start_monitoring)
            start_btn.grid(column=0, row=0, padx=2, pady=5)

            close_btn = ttk.Button(window, text="Close", command=self._stop)
            close_btn.grid(column=1, row=0, padx=2, pady=5)
        else:
            stop_btn = ttk.Button(window, text="Stop Script", command=self._stop)
            stop_btn.grid(column=0, row=0, padx=2, pady=5)

            close_btn = ttk.Button(window, text="Close Window", command=window.destroy)
            close_btn.grid(column=1, row=0, padx=2, pady=5)

        startup_btn = ttk.Button(
            window, text="RUN ON STARTUP", command=self._add_to_startup
        )
        startup_btn.grid(column=2, row=0, padx=2, pady=5)

    def _start_monitoring(self) -> None:
        """Start the keyboard monitoring."""
        self._root.destroy()

        # Create monitoring window
        self._monitoring_window = tk.Tk()
        self._setup_window(self._monitoring_window)
        self._create_menu(self._monitoring_window, is_main=False)
        self._create_buttons(self._monitoring_window, is_main=False)

        # Start the keyboard hook
        self._start_hook()
        self._running = True

        self._monitoring_window.mainloop()

    def _start_hook(self) -> None:
        """Start the keyboard hook for monitoring."""
        try:
            import pyHook  # type: ignore[import-untyped]
            import pythoncom  # type: ignore[import-untyped]

            self._hook_manager = pyHook.HookManager()
            self._hook_manager.KeyDown = self._on_keystroke
            self._hook_manager.HookKeyboard()

            # Process Windows messages in the Tkinter event loop
            def pump_messages() -> None:
                if self._running:
                    pythoncom.PumpWaitingMessages()
                    self._monitoring_window.after(10, pump_messages)

            self._monitoring_window.after(10, pump_messages)

        except ImportError as e:
            messagebox.showerror(
                "Import Error",
                f"Failed to import required modules: {e}\n\n"
                "Please install pyHook and pywin32.",
            )

    def _on_keystroke(self, event: object) -> bool:
        """Handle keystroke events from the hook.

        Args:
            event: pyHook keyboard event.

        Returns:
            True to allow the keystroke, False to block.
        """
        # Check for paranoid mode message display
        from duckhunt.policies import ParanoidPolicy

        if isinstance(self.detector.policy, ParanoidPolicy):
            if self.detector.policy.should_show_message:
                messagebox.showwarning(
                    "KeyInjection Detected",
                    "Someone might be trying to inject keystrokes into your computer.\n"
                    "Please check your ports or any strange programs running.\n"
                    "Enter your Password to unlock keyboard.",
                )

        # Track if we were locked before processing
        was_locked = (
            isinstance(self.detector.policy, ParanoidPolicy)
            and self.detector.policy.is_locked
        )

        result = self.detector.process_keystroke(
            key=event.Key,  # type: ignore[attr-defined]
            ascii_code=event.Ascii,  # type: ignore[attr-defined]
            timestamp=event.Time,  # type: ignore[attr-defined]
            window_name=event.WindowName or "",  # type: ignore[attr-defined]
            is_injected=event.Injected != 0,  # type: ignore[attr-defined]
        )

        # Show success message if we just unlocked
        if (
            was_locked
            and isinstance(self.detector.policy, ParanoidPolicy)
            and not self.detector.policy.is_locked
        ):
            messagebox.showinfo("KeyInjection Detected", "Correct Password!")

        return result

    def _stop(self) -> None:
        """Stop the application."""
        self._running = False
        sys.exit(0)

    def _show_about(self) -> None:
        """Open the about page in a browser."""
        webbrowser.open_new(self.ABOUT_URL)

    def _toggle_fullscreen(self, window: tk.Tk | tk.Toplevel) -> None:
        """Toggle fullscreen mode with Escape key to exit.

        Args:
            window: Window to make fullscreen.
        """
        window.attributes("-fullscreen", True)
        window.bind("<Escape>", lambda e: window.attributes("-fullscreen", False))

    def _add_to_startup(self) -> None:
        """Add the application to Windows startup."""
        try:
            username = getpass.getuser()
            startup_path = Path(
                rf"C:\Users\{username}\AppData\Roaming\Microsoft\Windows"
                r"\Start Menu\Programs\Startup"
            )

            script_dir = Path(__file__).parent.parent
            bat_content = f'start "" python -m duckhunt\n'

            bat_file = startup_path / "duckhunt.bat"
            bat_file.write_text(bat_content, encoding="utf-8")

            messagebox.showinfo(
                "Startup Added",
                f"DuckHunt will now run on startup.\nBatch file created at:\n{bat_file}",
            )
        except OSError as e:
            messagebox.showerror("Error", f"Failed to add to startup: {e}")

    def run(self) -> None:
        """Run the application main loop."""
        self._root.mainloop()


def create_app(config: Config, detector: KeystrokeDetector) -> DuckHuntApp:
    """Create the DuckHunt application.

    Args:
        config: DuckHunt configuration.
        detector: Keystroke detector instance.

    Returns:
        Configured DuckHuntApp instance.
    """
    return DuckHuntApp(config, detector)
