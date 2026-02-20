# Text Exploder for Windows

A background utility that listens for specific text abbreviations and replaces them globally across any application in Windows 11. Built with Python, `keyboard`, `tkinter`, and `pystray`.

## Features

- Global text replacement across all applications.
- Unobtrusive system tray icon showing the app is running.
- Cross-application compatibility using low-level keyboard hooks.
- A quick settings UI built in Tkinter to dynamically add, edit, or delete items on the fly.
- Saves directly to a simple `config.json`.

## Quick Start

You should be able to run this without opening a console window by double-clicking:
`start_textexpander.vbs`

1. The app will spawn an icon in your system tray (bottom right corner, looks like a tiny blue square).
2. Start typing. Try typing `;brb` or `;em1` (the defaults).

## How to edit abbreviations

1. Right-click the system tray icon and select **Settings**.
2. A window will appear showing your current definitions.
3. You can use this window to add new ones or adjust existing ones. As soon as you hit **Add / Update** or **Delete**, the changes are instantly live across your OS.

## How to run on startup

To ensure this runs every time you start Windows:

1. Press `Win + R` to open the Run dialog.
2. Type `shell:startup` and hit Enter. This will open your Startup folder.
3. Right click on `start_textexpander.vbs` in the TextExpander folder and select "Copy".
4. Go to the Startup folder, right click the empty space, and select "Paste shortcut".

**Note regarding Administrator applications**: Windows UAC prevents regular applications from intercepting keys inside applications that are running "As Administrator" (like Task Manager, or elevated command prompts). If you want the Text Expander to work *inside* administrator applications, you must run the Text Expander itself as an Administrator or bypass UAC for the script on startup.
