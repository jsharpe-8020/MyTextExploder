import json
import os
import sys
import subprocess
import time
import threading
import keyboard
import pyperclip
import pystray
from PIL import Image, ImageDraw
import ui
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

# Migrate existing local config to AppData on first run
_local_config = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
if os.path.exists(_local_config) and not os.path.exists(CONFIG_FILE):
    import shutil
    shutil.copy2(_local_config, CONFIG_FILE)
icon_instance = None

TYPED_BUFFER = ""
MAX_BUFFER = 100
current_handlers = {}
hook_set = False
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

# ── Settings hotkey: Ctrl+Shift+Alt ──
SETTINGS_HOTKEY = 'ctrl+shift+alt'

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
    elif len(name) == 1:
        TYPED_BUFFER += name
        # Track word characters; punctuation triggers word boundary
        if name.isalnum():
            WORD_BUFFER += name
        else:
            _queue_word()
    else:
        # Ignore modifier keys and other special keys
        return
        
    TYPED_BUFFER = TYPED_BUFFER[-MAX_BUFFER:]
    
    for variant, handler in current_handlers.items():
        if TYPED_BUFFER.endswith(variant):
            TYPED_BUFFER = ""
            threading.Thread(target=handler, daemon=True).start()
            break

def reload_abbreviations():
    global current_handlers, hook_set
    
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

def create_image():
    width, height = 64, 64
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    dc = ImageDraw.Draw(image)
    # Green "T" block
    dc.rectangle((16, 16, 48, 48), fill=(0, 175, 102))
    return image

def on_settings(icon, item):
    # Open the UI in a separate thread so it doesn't block the system tray
    def open_ui():
        ui.open_settings_window(reload_abbreviations)
    
    threading.Thread(target=open_ui, daemon=True).start()

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
    # Initialize frequency database
    frequency_db.init_db()
    
    # Register for auto-startup (idempotent)
    register_startup()
    
    # Load initial abbreviations
    reload_abbreviations()
    
    # Register global hotkey: Ctrl+Shift+Alt to open Settings
    def _open_settings_hotkey():
        # Tkinter crashes when spawned from a keyboard background thread.
        # Spawning ui.py as a completely separate process acts as a bulletproof workaround.
        ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui.py")
        subprocess.Popen([sys.executable, ui_path], creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        
        # We also need to reload abbreviations here in main after a short delay
        # in case the user saves new ones in the UI process.
        def _poll_reload():
            time.sleep(2)  # Give user time to open and edit
            # Read modified time of config
            if os.path.exists(CONFIG_FILE):
                last_mtime = os.path.getmtime(CONFIG_FILE)
                for _ in range(300): # Poll for 5 mins
                    time.sleep(1)
                    if not os.path.exists(CONFIG_FILE): continue
                    current_mtime = os.path.getmtime(CONFIG_FILE)
                    if current_mtime > last_mtime:
                        reload_abbreviations()
                        last_mtime = current_mtime
        threading.Thread(target=_poll_reload, daemon=True).start()
    
    # Suppress=False is critical here; suppressing modifiers on Windows breaks the keyboard chain
    keyboard.add_hotkey(SETTINGS_HOTKEY, _open_settings_hotkey, suppress=False)
    
    # Start background flush thread for frequency tracking
    
    # Start background flush thread for frequency tracking
    flush_thread = threading.Thread(target=_flush_loop, daemon=True)
    flush_thread.start()
    
    # Setup and run system tray
    setup_tray()
    icon_instance.run()

if __name__ == "__main__":
    main()
