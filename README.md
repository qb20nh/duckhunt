# DuckHunt

![DuckHunt Logo](duckhunt.32.png)

[![PyPI version](https://img.shields.io/pypi/v/duckhunt-win.svg?logo=pypi&logoColor=white)](https://pypi.org/project/duckhunt-win/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/qb20nh/duckhunt/actions/workflows/release.yml/badge.svg)](https://github.com/qb20nh/duckhunt/actions/workflows/release.yml)

**Prevent RubberDucky and Keystroke Injection Attacks**

DuckHunt protects Windows from "**RubberDucky**" attacks by monitoring typing patterns and immediately locking the system upon detecting inhumanly fast keystroke inputs.

## ✨ Features

* **Heuristic Detection**: Analyzes typing speed and burst patterns to distinguish between human typing and automated scripts.
* **Background Protection**: Runs unobtrusively in the system tray.
* **Smart Session Monitoring**: Event-based detection automatically pauses monitoring when the workstation is locked (no polling overhead).
* **Secure & Robust**:
  * Uses a split-process architecture (GUI + Daemon) for stability.
  * Single-instance enforcement prevents conflicts.
  * Auto-restarting daemon ensures continuous protection.
* **Configurable**: Adjustable sensitivity thresholds to match your typing style.

## 📦 Installation

**Prerequisites:** Python 3.10 or higher.

1. **Install from PyPI:**

   ```bash
   pip install duckhunt-win
   ```

2. **Clone the repository (for development):**

   ```bash
   git clone https://github.com/qb20nh/duckhunt.git
   cd duckhunt
   ```

3. **Install dependencies:**

```bash
pip install .
```

*For development, you can install with dev dependencies:*

```bash
pip install -e .[dev]
```

## 🚀 Usage

### Starting DuckHunt

You can start the application by running the module directly:

```bash
python -m duckhunt-win
```

Or by running the executable if you have downloaded the [latest release](https://github.com/qb20nh/duckhunt/releases/latest).

### System Tray Controls

Once running, DuckHunt appears in your system tray:

* **Left-Click / Toggle**: Enable or Disable monitoring.
* **Settings**: Open the configuration window to adjust sensitivity.
* **Exit**: Quit the application and stop the background protection daemon.

### How it Works

1. **Monitoring**: The `Daemon` process listens to global keystrokes using low-level hooks.
2. **Detection**: If the typing speed exceeds the configured **Threshold** (default 30ms/key) or exhibits suspicious **Bursts**, the detector flags the activity.
3. **Reaction**: The workstation is immediately locked via Windows API.
4. **Notification**: When you unlock your computer, DuckHunt notifies you that an attack was blocked.

## ⚙️ Configuration

You can configure DuckHunt via the Settings window or by creating a `duckhunt.toml` (or `duckhunt.conf`) file in your home directory or the application folder.

| Setting | Default | Description |
| :--- | :--- | :--- |
| `threshold` | `30` | Average interval between keys in milliseconds. Lower means faster typing is allowed (less sensitive). |
| `history_size` | `25` | Number of recent keystrokes to analyze for average speed. |
| `burst_keys` | `10` | Number of keys in a sequence to trigger "burst" detection. |
| `burst_window_ms` | `100` | Maximum time (ms) allowing `burst_keys` to be pressed before flagging as suspicious. |
| `allow_auto_type` | `true` | (Experimental) Allow software simulated keys. |

## 📄 License

MIT License
