"""DuckHunt entry point."""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    """Run the DuckHunt application."""
    parser = argparse.ArgumentParser(
        prog="duckhunt",
        description="Prevent RubberDucky and keystroke injection attacks",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to configuration file (duckhunt.conf or duckhunt.toml)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without GUI (console mode)",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="%(prog)s 1.0.0",
    )

    args = parser.parse_args()

    # Load configuration
    from pathlib import Path

    from duckhunt.config import Config

    config_path = Path(args.config) if args.config else None
    config = Config.load(config_path)

    # Create policy and detector
    from duckhunt.detector import KeystrokeDetector
    from duckhunt.policies import create_policy

    policy = create_policy(config)
    detector = KeystrokeDetector(
        config=config,
        policy=policy,
        on_intrusion=lambda msg: print(msg),
    )

    if args.headless:
        # Headless mode - just hook keyboard and run
        return run_headless(detector)

    # GUI mode
    from duckhunt.gui import create_app

    app = create_app(config, detector)
    app.run()
    return 0


def run_headless(detector: KeystrokeDetector) -> int:
    """Run in headless (console) mode.

    Args:
        detector: Configured keystroke detector.

    Returns:
        Exit code.
    """
    try:
        import pyHook  # type: ignore[import-untyped]
        import pythoncom  # type: ignore[import-untyped]
    except ImportError as e:
        print(f"Error: Failed to import required modules: {e}", file=sys.stderr)
        print("Please install pyHook and pywin32.", file=sys.stderr)
        return 1

    print("DuckHunt is now running in headless mode...")
    print("Press Ctrl+C to stop.")

    def on_keystroke(event: object) -> bool:
        return detector.process_keystroke(
            key=event.Key,  # type: ignore[attr-defined]
            ascii_code=event.Ascii,  # type: ignore[attr-defined]
            timestamp=event.Time,  # type: ignore[attr-defined]
            window_name=event.WindowName or "",  # type: ignore[attr-defined]
            is_injected=event.Injected != 0,  # type: ignore[attr-defined]
        )

    hook_manager = pyHook.HookManager()
    hook_manager.KeyDown = on_keystroke
    hook_manager.HookKeyboard()

    try:
        pythoncom.PumpMessages()
    except KeyboardInterrupt:
        print("\nDuckHunt stopped.")

    return 0


# Import for type checking
from duckhunt.detector import KeystrokeDetector

if __name__ == "__main__":
    sys.exit(main())
