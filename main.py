import json
import os
import sys
import subprocess
import time
import threading
import ctypes
import keyboard
import pyperclip
import pystray
from PIL import Image, ImageDraw
import datetime
import frequency_db

# Prevent pythonw.exe silent crashes by providing dummy file handles for stdout/stderr
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "MyTextExploder")
os.makedirs(APPDATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APPDATA_DIR, "config.json")
UI_LAUNCH_LOG = os.path.join(APPDATA_DIR, "ui_launch.log")

# Migrate existing local config to AppData on first run
_local_config = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
if os.path.exists(_local_config) and not os.path.exists(CONFIG_FILE):
    import shutil
    shutil.copy2(_local_config, CONFIG_FILE)
icon_instance = None
_single_instance_mutex = None
MUTEX_NAME = "Global\\MyTextExploderSingleton"

TYPED_BUFFER = ""
MAX_BUFFER = 100
current_handlers = {}
hook_set = False
settings_hotkey_registered = False
is_writing = False

# ── Frequency tracking state ──
WORD_BUFFER = ""
PENDING_PHRASES = []     # Single words queued for recording
RECENT_WORDS = []        # Rolling window of recent words for n-gram generation
MAX_RECENT_WORDS = 3     # Keep last N words for bigram/trigram generation
PHRASE_LOCK = threading.Lock()
FLUSH_INTERVAL = 30      # seconds
PRUNE_COUNTER = 0        # Prune DB every Nth flush cycle
PRUNE_EVERY = 10         # Run prune_db every 10 flush cycles (~5 min)

# ── Settings hotkey: Ctrl+Alt+T ──
SETTINGS_HOTKEY = 'ctrl+alt+t'
TOKEN_KEY_ALIASES = {
    "minus": "-",
    "hyphen": "-",
    "dash": "-",
    "underscore": "_",
    "grave": "`",
    "backtick": "`",
    "oem_3": "`",
    "num 0": "0",
    "num 1": "1",
    "num 2": "2",
    "num 3": "3",
    "num 4": "4",
    "num 5": "5",
    "num 6": "6",
    "num 7": "7",
    "num 8": "8",
    "num 9": "9",
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}

def _launch_settings_process():
    """Launch settings via a detached helper after the hotkey keys are released."""
    if getattr(_launch_settings_process, "_inflight", False):
        return
    _launch_settings_process._inflight = True

    def _launch_detached():
        try:
            project_dir = os.path.dirname(os.path.abspath(__file__))
            # Launch after modifiers are released to avoid focus/foreground issues.
            deadline = time.time() + 1.0
            while time.time() < deadline:
                try:
                    if not (keyboard.is_pressed("ctrl") or keyboard.is_pressed("alt") or keyboard.is_pressed("t")):
                        break
                except Exception:
                    break
                time.sleep(0.02)

            launcher_vbs = os.path.join(project_dir, "open_settings_window.vbs")
            with open(UI_LAUNCH_LOG, "a", encoding="utf-8") as logf:
                logf.write(f"{datetime.datetime.now().isoformat()} launch settings via detached helper\n")

            if os.path.exists(launcher_vbs):
                subprocess.Popen(
                    ["wscript.exe", launcher_vbs],
                    cwd=project_dir,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0,
                )
            else:
                # Fallback if the helper file is missing.
                ui_path = os.path.join(project_dir, "ui.py")
                python_exe = sys.executable or "python"
                pythonw_exe = python_exe[:-10] + "pythonw.exe" if python_exe.lower().endswith("python.exe") else python_exe
                if not os.path.exists(pythonw_exe):
                    pythonw_exe = python_exe
                subprocess.Popen(
                    [pythonw_exe, ui_path],
                    cwd=project_dir,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0,
                )
        except Exception as e:
            try:
                with open(UI_LAUNCH_LOG, "a", encoding="utf-8") as logf:
                    logf.write(f"{datetime.datetime.now().isoformat()} launcher exception: {e!r}\n")
            except Exception:
                pass
        finally:
            _launch_settings_process._inflight = False

    threading.Thread(target=_launch_detached, daemon=True).start()

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def _paste_replace(abbrev_str, replacement):
    """Erase the abbreviation with backspaces, then paste replacement via clipboard."""
    global is_writing
    is_writing = True
    try:
        # Save current clipboard
        try:
            old_clip = pyperclip.paste()
        except Exception:
            old_clip = ""
        
        # Erase the typed abbreviation
        for _ in range(len(abbrev_str)):
            keyboard.press_and_release('backspace')
        time.sleep(0.02)
        
        # Paste replacement via clipboard (instant)
        pyperclip.copy(replacement)
        keyboard.press_and_release('ctrl+v')
        time.sleep(0.05)
        
        # Restore original clipboard
        pyperclip.copy(old_clip)
    finally:
        is_writing = False

def make_dynamic_callback(abbrev_str, repl_str):
    def callback():
        now = datetime.datetime.now()
        final_repl = repl_str
        if final_repl == "YYYYMMDD_HHMMSS":
             final_repl = now.strftime("%Y%m%d_%H%M%S")
        else:
             final_repl = final_repl.replace("{{YYYYMMDD_HHMMSS}}", now.strftime("%Y%m%d_%H%M%S"))
             final_repl = final_repl.replace("{{YYYYMMDD}}", now.strftime("%Y%m%d"))
             final_repl = final_repl.replace("{{YYYY-MM-DD}}", now.strftime("%Y-%m-%d"))
             final_repl = final_repl.replace("{{HHMMSS}}", now.strftime("%H%M%S"))
        _paste_replace(abbrev_str, final_repl)
    return callback

def make_static_callback(abbrev_str, repl_str):
    def callback():
        _paste_replace(abbrev_str, repl_str)
    return callback

def _queue_word():
    """Extract the current word from WORD_BUFFER, queue it, and generate n-grams."""
    global WORD_BUFFER
    word = WORD_BUFFER.strip()
    WORD_BUFFER = ""
    if not word:
        return
    with PHRASE_LOCK:
        # Always queue the single word (frequency_db filters by length/stop words)
        if len(word) >= 4:
            PENDING_PHRASES.append(word)
        # Build n-grams from recent words
        RECENT_WORDS.append(word.lower())
        if len(RECENT_WORDS) > MAX_RECENT_WORDS:
            RECENT_WORDS.pop(0)
        # Generate bigrams and trigrams
        if len(RECENT_WORDS) >= 2:
            PENDING_PHRASES.append(" ".join(RECENT_WORDS[-2:]))
        if len(RECENT_WORDS) >= 3:
            PENDING_PHRASES.append(" ".join(RECENT_WORDS[-3:]))


def on_key_event(event):
    global TYPED_BUFFER, WORD_BUFFER, is_writing
    if event.event_type != keyboard.KEY_DOWN:
        return

    if is_writing:
        return
        
    name = event.name
    if not name:
        return
        
    if name == 'space':
        TYPED_BUFFER += ' '
        _queue_word()
    elif name == 'enter':
        TYPED_BUFFER += '\n'
        _queue_word()
    elif name == 'backspace':
        TYPED_BUFFER = TYPED_BUFFER[:-1]
        WORD_BUFFER = WORD_BUFFER[:-1]
    else:
        mapped_name = TOKEN_KEY_ALIASES.get(name)
        if mapped_name:
            TYPED_BUFFER += mapped_name
            if mapped_name == "`" and WORD_BUFFER:
                _queue_word()
            WORD_BUFFER += mapped_name
            TYPED_BUFFER = TYPED_BUFFER[-MAX_BUFFER:]
            for variant, handler in current_handlers.items():
                if TYPED_BUFFER.endswith(variant):
                    TYPED_BUFFER = ""
                    threading.Thread(target=handler, daemon=True).start()
                    break
            return
        if len(name) != 1:
            # Ignore modifier keys and other special keys
            return

        TYPED_BUFFER += name
        # Track token characters; allow common identifier chars like -, _, and `.
        if name.isalnum() or name in "-_`":
            if name == "`" and WORD_BUFFER:
                _queue_word()
            WORD_BUFFER += name
        else:
            _queue_word()
        
    TYPED_BUFFER = TYPED_BUFFER[-MAX_BUFFER:]
    
    for variant, handler in current_handlers.items():
        if TYPED_BUFFER.endswith(variant):
            TYPED_BUFFER = ""
            threading.Thread(target=handler, daemon=True).start()
            break

def reload_abbreviations():
    global current_handlers, hook_set, settings_hotkey_registered
    
    config = load_config()
    new_handlers = {}
    
    for abbrev, replacement in config.items():
        if abbrev and replacement:
            variants = {abbrev, abbrev.lower(), abbrev.upper(), abbrev.capitalize()}
            for variant in variants:
                if "{{" in replacement or replacement == "YYYYMMDD_HHMMSS":
                    new_handlers[variant] = make_dynamic_callback(variant, replacement)
                else:
                    new_handlers[variant] = make_static_callback(variant, replacement)
                    
    current_handlers = new_handlers
    
    if not hook_set:
        keyboard.hook(on_key_event)
        hook_set = True
    if not settings_hotkey_registered:
        keyboard.add_hotkey(
            SETTINGS_HOTKEY,
            _launch_settings_process,
            suppress=False,
            trigger_on_release=True,
        )
        settings_hotkey_registered = True

def create_image():
    width, height = 64, 64
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    dc = ImageDraw.Draw(image)
    # Green "T" block
    dc.rectangle((16, 16, 48, 48), fill=(0, 175, 102))
    return image

def on_settings(icon, item):
    _launch_settings_process()

def flush_pending_phrases():
    """Write any queued phrases to the database."""
    with PHRASE_LOCK:
        batch = PENDING_PHRASES.copy()
        PENDING_PHRASES.clear()
    if batch:
        frequency_db.record_phrases_batch(batch)


def _flush_loop():
    """Background loop that periodically flushes queued phrases to SQLite and prunes."""
    global PRUNE_COUNTER
    while True:
        time.sleep(FLUSH_INTERVAL)
        flush_pending_phrases()
        # Periodically prune to keep DB bounded
        PRUNE_COUNTER += 1
        if PRUNE_COUNTER >= PRUNE_EVERY:
            PRUNE_COUNTER = 0
            try:
                frequency_db.prune_db()
            except Exception:
                pass  # Don't crash the flush loop


def on_quit(icon, item):
    flush_pending_phrases()  # Final flush before exit
    keyboard.unhook_all()
    icon.stop()

def setup_tray():
    global icon_instance
    menu = pystray.Menu(
        pystray.MenuItem('Settings', on_settings),
        pystray.MenuItem('Quit', on_quit)
    )
    image = create_image()
    icon_instance = pystray.Icon("TextExploder", image, "My Text Exploder", menu)
    
def register_startup():
    """Create a shortcut in the Windows Startup folder so TextExploder runs on login."""
    try:
        import subprocess
        # Get the startup folder path
        startup_dir = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
        )
        if not os.path.isdir(startup_dir):
            return  # Not a standard Windows layout
        
        shortcut_path = os.path.join(startup_dir, "MyTextExploder.lnk")
        if os.path.exists(shortcut_path):
            return  # Already registered
        
        # Target: the VBS launcher in the project directory
        project_dir = os.path.dirname(os.path.abspath(__file__))
        vbs_path = os.path.join(project_dir, "start_mytextexploder.vbs")
        if not os.path.exists(vbs_path):
            return  # VBS launcher not found
        
        # Create shortcut using PowerShell (works without extra dependencies)
        ps_script = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{shortcut_path}"); '
            f'$s.TargetPath = "{vbs_path}"; '
            f'$s.WorkingDirectory = "{project_dir}"; '
            f'$s.Description = "My Text Exploder"; '
            f'$s.Save()'
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, timeout=10
        )
    except Exception:
        pass  # Non-critical — don't crash the app


def main():
    global _single_instance_mutex
    # Prevent duplicate tray instances.
    _single_instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return

    # Initialize frequency database
    frequency_db.init_db()
    
    # Register for auto-startup (idempotent)
    register_startup()
    
    # Load initial abbreviations
    reload_abbreviations()
    
    # We poll for config changes to reload abbreviations if the separate UI process modifies them
    def _poll_reload():
        if os.path.exists(CONFIG_FILE):
            last_mtime = os.path.getmtime(CONFIG_FILE)
            while True:
                time.sleep(2)
                if not os.path.exists(CONFIG_FILE): continue
                current_mtime = os.path.getmtime(CONFIG_FILE)
                if current_mtime > last_mtime:
                    reload_abbreviations()
                    last_mtime = current_mtime
    threading.Thread(target=_poll_reload, daemon=True).start()
    
    # Start background flush thread for frequency tracking
    flush_thread = threading.Thread(target=_flush_loop, daemon=True)
    flush_thread.start()
    
    # Setup and run system tray
    setup_tray()
    icon_instance.run()

if __name__ == "__main__":
    main()

