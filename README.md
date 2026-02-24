# My Text Exploder for Windows

A background utility that listens for specific text abbreviations and replaces them globally across any application in Windows 11. Built with Python, `keyboard`, `tkinter`, and `pystray`.

## Features

- **Global text replacement** across all applications
- **System tray icon** showing the app is running
- **Ctrl+Alt+T hotkey** to open Settings from anywhere
- **Frequency tracking** — learns which words you type most often via SQLite
- **Smart suggestions** — recommends your most-typed phrases as shortcut candidates
- **Tracked words tab** — view everything in the frequency database
- **Auto-start on login** — registers itself in the Windows Startup folder
- **Database pruning** — automatic cleanup keeps the frequency DB lean (5K row cap, 30-day stale removal)

## Quick Start

Double-click `start_mytextexploder.vbs` to launch silently in the background.

1. The app will spawn an icon in your system tray (bottom right corner, looks like a green square).
2. Start typing. Try typing `;brb` or `;em1` (the defaults).

## How to Edit Abbreviations

**Option 1: Hotkey** — Press `Ctrl+Alt+T` from anywhere to open Settings.

**Option 2: System Tray** — Right-click the system tray icon and select **Settings**.

The Settings window has three tabs:

| Tab | Purpose |
|-----|---------|
| **Shortcuts** | Add, edit, and delete abbreviation mappings |
| **Suggestions** | See your most-typed words and promote them to shortcuts |
| **Tracked** | Browse all tracked words/phrases and their frequencies |

## How to Run on Startup

The app automatically registers itself in your Windows Startup folder on first run. To manually add it:

1. Press `Win + R` → type `shell:startup` → Enter
2. Right-click `start_mytextexploder.vbs` → Copy
3. Paste a shortcut into the Startup folder

## Requirements

```
pip install keyboard pyperclip pystray pillow
```

## Important Notes

- **Administrator apps**: Windows UAC prevents regular apps from intercepting keys in elevated applications (Task Manager, admin command prompts). Run Text Exploder as Administrator if you need it to work inside those apps.
- **Config location**: Abbreviations are stored in `%APPDATA%/MyTextExploder/config.json`
- **Frequency database**: Tracked phrases are stored in `%APPDATA%/MyTextExploder/frequency.db`
