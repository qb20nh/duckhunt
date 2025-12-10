"""
Settings Window GUI (View).
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any

from duckhunt_win.config import Config
from duckhunt_win.ipc import MSG_CONFIG
from duckhunt_win.utils import get_resource_path


class SettingsWindow:
    """Settings GUI window."""

    def __init__(self, controller: Any, root: tk.Tk, config: Config):
        self.controller = controller # DuckHuntController (Protocol/Any to avoid circular import)
        self.root = root
        self._window: tk.Toplevel | None = None
        
        # Current config values
        self.threshold = tk.IntVar(value=config.threshold)
        self.history_size = tk.IntVar(value=config.history_size)
        self.burst_keys = tk.IntVar(value=config.burst_keys)
        self.burst_window_ms = tk.IntVar(value=config.burst_window_ms)
        self.allow_auto_type = tk.BooleanVar(value=config.allow_auto_type)
        self.run_on_startup = tk.BooleanVar(value=controller.check_startup())

    def show(self) -> None:
        """Show the settings window."""
        if self._window and self._window.winfo_exists():
            self._window.deiconify()
            self._window.attributes("-topmost", True)
            self._window.lift()
            self._window.focus_force()
            self._window.attributes("-topmost", False)
            return

        self._window = tk.Toplevel(self.root)
        self._window.title("DuckHunt Settings")
        self._window.geometry("350x450")
        self._window.resizable(False, False)
        
        # Force to top then release to ensure visibility
        self._window.attributes("-topmost", True)
        self._window.after(10, lambda: self._window.attributes("-topmost", False))

        # Set window icon
        icon_path = get_resource_path("resources/favicon.ico")
        if icon_path.exists():
            self._window.iconbitmap(icon_path)
        if icon_path.exists():
            self._window.iconbitmap(icon_path)

        # Layout - Bottom Buttons Frame first to ensure visibility
        btn_frame = ttk.Frame(self._window, padding=(10, 10, 10, 10))
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Button(btn_frame, text="Save & Apply", command=self.save).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Cancel", command=self._window.destroy).pack(
            side=tk.RIGHT, padx=5
        )

        # Separator line above buttons
        ttk.Separator(self._window, orient=tk.HORIZONTAL).pack(side=tk.BOTTOM, fill=tk.X)

        # Main Layout Frame
        main_frame = ttk.Frame(self._window, padding=15)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Threshold
        ttk.Label(main_frame, text="Speed Threshold (ms):").pack(anchor=tk.W, pady=(0, 2))
        ttk.Label(
            main_frame,
            text="Lower = more sensitive (detects faster typing)",
            font=("", 8),
        ).pack(anchor=tk.W)
        ttk.Scale(
            main_frame, from_=5, to=100, variable=self.threshold, orient=tk.HORIZONTAL
        ).pack(fill=tk.X, pady=(0, 10))
        ttk.Label(main_frame, textvariable=self.threshold).pack()

        # History Size
        ttk.Label(main_frame, text="History Size:").pack(anchor=tk.W, pady=(0, 2))
        ttk.Scale(
            main_frame,
            from_=5,
            to=100,
            variable=self.history_size,
            orient=tk.HORIZONTAL,
        ).pack(fill=tk.X, pady=(0, 10))
        ttk.Label(main_frame, textvariable=self.history_size).pack()

        # Burst Settings
        ttk.Label(main_frame, text="Burst Keys (count):").pack(anchor=tk.W, pady=(0, 2))
        ttk.Scale(
            main_frame, from_=3, to=50, variable=self.burst_keys, orient=tk.HORIZONTAL
        ).pack(fill=tk.X, pady=(0, 2))
        ttk.Label(main_frame, textvariable=self.burst_keys).pack()

        ttk.Label(main_frame, text="Burst Window (ms):").pack(anchor=tk.W, pady=(0, 2))
        ttk.Scale(
            main_frame,
            from_=50,
            to=1000,
            variable=self.burst_window_ms,
            orient=tk.HORIZONTAL,
        ).pack(fill=tk.X, pady=(0, 10))
        ttk.Label(main_frame, textvariable=self.burst_window_ms).pack()

        # Auto-type
        ttk.Checkbutton(
            main_frame,
            text="Allow Auto-Type (Software Injected)",
            variable=self.allow_auto_type,
        ).pack(anchor=tk.W, pady=(0, 2))

        # Startup
        ttk.Checkbutton(
            main_frame, text="Run on Windows Startup", variable=self.run_on_startup
        ).pack(anchor=tk.W, pady=(0, 5))

        # Handle window close
        self._window.protocol("WM_DELETE_WINDOW", self._window.destroy)

    def save(self) -> None:
        """Save settings and notify daemon."""
        new_config = {
            "threshold": self.threshold.get(),
            "history_size": self.history_size.get(),
            "burst_keys": self.burst_keys.get(),
            "burst_window_ms": self.burst_window_ms.get(),
            "allow_auto_type": self.allow_auto_type.get(),
        }

        # Apply startup setting
        self.controller.toggle_startup(self.run_on_startup.get())

        # Send to daemon
        self.controller.send_command(MSG_CONFIG, new_config)

        # Close window
        if self._window:
            self._window.destroy()
