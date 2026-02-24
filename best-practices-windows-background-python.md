# Best Practices: Windows Background Python Apps

Lessons learned from building MyTextExploder — a background Python utility that uses keyboard hooks, system tray icons, and Tkinter UI windows on Windows.

---

## 1. Running Without a Console (`pythonw.exe`)

### Problem

When Python runs via `pythonw.exe`, `sys.stdout` and `sys.stderr` are set to `None`. Any library or code that calls `print()`, `logging.info()`, or writes to these streams will throw a silent `AttributeError` and crash the current thread without any visible error.

### Solution

At the very top of your entry point, before any imports that might trigger logging:

```python
import sys, os
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
```

### Debugging Tip

Write errors to a log file in `%APPDATA%` instead of relying on console output:

```python
UI_LAUNCH_LOG = os.path.join(APPDATA_DIR, "ui_launch.log")
try:
    do_something()
except Exception as e:
    with open(UI_LAUNCH_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} ERROR: {e!r}\n")
```

---

## 2. Spawning GUI Windows from Background Threads

### Problem

Tkinter uses COM objects internally on Windows. These COM objects are bound to the thread that creates them. When you try to create a `tk.Tk()` window from a background thread (e.g., a `keyboard` hook callback), the window may flash in the taskbar and then immediately crash.

### What Doesn't Work

```python
# ❌ Crashes silently under pythonw.exe
def on_hotkey():
    threading.Thread(target=lambda: ui.open_settings_window()).start()
```

### What Works

Launch the UI as a completely separate process:

```python
# ✅ Bulletproof — separate process, separate thread safety context
def on_hotkey():
    subprocess.Popen(["pythonw.exe", "ui.py"])
```

For even more reliability, use a VBS wrapper script to handle the process launch:

```vbs
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw.exe ui.py", 0
```

### Config Synchronization

Since the UI runs in a separate process, it can't call back into the main process. Instead, poll the config file for changes:

```python
def _poll_reload():
    last_mtime = os.path.getmtime(CONFIG_FILE)
    while True:
        time.sleep(2)
        current_mtime = os.path.getmtime(CONFIG_FILE)
        if current_mtime > last_mtime:
            reload_config()
            last_mtime = current_mtime
```

---

## 3. Global Hotkeys with the `keyboard` Library

### Problem

`keyboard.add_hotkey()` has several Windows-specific quirks:

| Issue | Details |
|-------|---------|
| Modifier-only combos fail | `'ctrl+shift+alt'` (no letter) is never triggered |
| `suppress=True` breaks modifiers | Other apps stop receiving modifier key events |
| Conflicts with `keyboard.hook()` | Both use the same low-level hook; ordering matters |

### Solution

Always use a **modifier + letter** combo and set `suppress=False`:

```python
keyboard.add_hotkey(
    'ctrl+alt+t',
    callback,
    suppress=False,
    trigger_on_release=True,  # fires after keys released — avoids focus issues
)
```

### Registration Order

Register `keyboard.hook()` first, then `keyboard.add_hotkey()`. The hook processes raw events; the hotkey uses a higher-level abstraction.

---

## 4. Waiting for Key Release Before Launching UI

### Problem

If you launch a subprocess while modifier keys are still held down, the new window may not receive focus properly, or the OS may interpret the held keys as input to the new window.

### Solution

Wait for all hotkey keys to be released before launching:

```python
deadline = time.time() + 1.0
while time.time() < deadline:
    if not (keyboard.is_pressed("ctrl") or keyboard.is_pressed("alt")):
        break
    time.sleep(0.02)
# Now safe to launch the UI subprocess
```

---

## 5. VBS Wrappers for Silent Launch

### Why

- `pythonw.exe` alone still briefly flashes a process in the taskbar on some systems
- VBS scripts via `wscript.exe` are truly invisible
- They set the working directory correctly

### Template

```vbs
Set WshShell = CreateObject("WScript.Shell")
scriptPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run chr(34) & scriptPath & "\venv\Scripts\pythonw.exe" & chr(34) & " " & chr(34) & scriptPath & "\main.py" & chr(34), 0
Set WshShell = Nothing
```

---

## Summary Checklist

- [ ] Guard `sys.stdout`/`sys.stderr` at the top of the entry point
- [ ] Never spawn Tkinter from a background thread — use `subprocess.Popen`
- [ ] Use modifier+letter hotkeys (e.g., `ctrl+alt+t`), never modifier-only
- [ ] Set `suppress=False` and `trigger_on_release=True` on hotkeys
- [ ] Wait for key release before launching UI subprocesses
- [ ] Write errors to log files, never rely on console output
- [ ] Use VBS wrappers for truly invisible background launch
