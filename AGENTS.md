# TextExploder — Agent Context

## Project Overview

**MyTextExploder** is a Windows background utility that listens for text abbreviations and expands them globally across all applications. Built with Python, it uses low-level keyboard hooks (`keyboard` library), a system tray icon (`pystray`), and a Tkinter Settings UI launched as a separate process.

## Architecture

| Component | File | Purpose |
|-----------|------|---------|
| Core engine | `main.py` | Keyboard hook, abbreviation matching, frequency tracking, system tray |
| Settings UI | `ui.py` | Standalone Tkinter app (3 tabs: Shortcuts, Suggestions, Tracked) |
| Frequency DB | `frequency_db.py` | SQLite word/phrase tracking, n-gram support, pruning |
| VBS launchers | `start_mytextexploder.vbs`, `open_settings_window.vbs` | Silent background launch wrappers |
| Config | `%APPDATA%/MyTextExploder/config.json` | User abbreviation mappings |
| Frequency DB | `%APPDATA%/MyTextExploder/frequency.db` | SQLite tracking database |

## Critical Patterns

### 1. Background Process (pythonw.exe)

The app runs via `pythonw.exe` (no console window). This **nullifies `sys.stdout` and `sys.stderr`**, which causes silent crashes if any library writes to them. The fix at the top of `main.py` redirects both to `os.devnull`.

### 2. UI Must Launch as Subprocess

Tkinter **cannot** be spawned from a background keyboard-hook thread. It crashes silently due to COM thread-safety violations on Windows. The Settings UI is always launched as a **separate subprocess** (`open_settings_window.vbs` → `pythonw.exe ui.py`). Config changes are detected via file-modification polling.

### 3. Keyboard Hotkey Registration

`keyboard.add_hotkey()` requires a **trigger key** (a non-modifier key like a letter). Pure modifier combos like `ctrl+shift+alt` silently fail on Windows. The current hotkey is `ctrl+alt+t`. Use `trigger_on_release=True` and `suppress=False` for reliability.

### 4. Token Tracking

The `TOKEN_KEY_ALIASES` dictionary in `main.py` maps special key names (e.g., `"minus"` → `"-"`) so that hyphens, underscores, backticks, and numpad digits are properly tracked.

## Key Dependencies

- `keyboard` — Global keyboard hooks (requires admin for elevated apps)
- `pystray` + `Pillow` — System tray icon
- `pyperclip` — Clipboard-based text insertion
- `tkinter` — Settings UI (stdlib)

## Common Pitfalls

- **Never import `ui` in `main.py`** — `ui.py` runs as a separate process, not an in-process module
- **Never call `print()` without guarding stdout** — Will crash under `pythonw.exe`
- **Never spawn Tkinter from a `keyboard` callback thread** — Use `subprocess.Popen` instead
- **Always use `suppress=False`** with `keyboard.add_hotkey()` — Suppressing modifiers breaks the keyboard chain on some Windows systems

## Related Documents

- [Best Practices: Windows Background Python Apps](best-practices-windows-background-python.md)
- [README.md](README.md)
