import json
import os
import threading
import keyboard
import pystray
from PIL import Image, ImageDraw
import ui
import datetime

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

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def make_dynamic_callback(abbrev_str, repl_str):
    def callback():
        global is_writing
        is_writing = True
        try:
            final_repl = repl_str
            now = datetime.datetime.now()
            
            # Parse special strings and replace them with formatted datetime
            if final_repl == "YYYYMMDD_HHMMSS":
                 final_repl = now.strftime("%Y%m%d_%H%M%S")
            else:
                 final_repl = final_repl.replace("{{YYYYMMDD_HHMMSS}}", now.strftime("%Y%m%d_%H%M%S"))
                 final_repl = final_repl.replace("{{YYYYMMDD}}", now.strftime("%Y%m%d"))
                 final_repl = final_repl.replace("{{YYYY-MM-DD}}", now.strftime("%Y-%m-%d"))
                 final_repl = final_repl.replace("{{HHMMSS}}", now.strftime("%H%M%S"))
            
            keyboard.write('\b' * len(abbrev_str) + final_repl)
        finally:
            is_writing = False
    return callback

def make_static_callback(abbrev_str, repl_str):
    def callback():
        global is_writing
        is_writing = True
        try:
            keyboard.write('\b' * len(abbrev_str) + repl_str)
        finally:
            is_writing = False
    return callback

def on_key_event(event):
    global TYPED_BUFFER, is_writing
    if is_writing or event.event_type != keyboard.KEY_DOWN:
        return
        
    name = event.name
    if not name:
        return
        
    if name == 'space':
        TYPED_BUFFER += ' '
    elif name == 'enter':
        TYPED_BUFFER += '\n'
    elif name == 'backspace':
        TYPED_BUFFER = TYPED_BUFFER[:-1]
    elif len(name) == 1:
        TYPED_BUFFER += name
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
    # Generate a simple generic icon for the system tray
    width, height = 64, 64
    image = Image.new('RGB', (width, height), color=(40, 44, 52))
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill=(97, 175, 239))
    return image

def on_settings(icon, item):
    # Open the UI in a separate thread so it doesn't block the system tray
    def open_ui():
        ui.open_settings_window(reload_abbreviations)
    
    threading.Thread(target=open_ui, daemon=True).start()

def on_quit(icon, item):
    keyboard.unhook_all()
    icon.stop()

def setup_tray():
    global icon_instance
    menu = pystray.Menu(
        pystray.MenuItem('Settings', on_settings),
        pystray.MenuItem('Quit', on_quit)
    )
    image = create_image()
    icon_instance = pystray.Icon("TextExploder", image, "Text Exploder", menu)
    
def main():
    # Load initial abbreviations
    reload_abbreviations()
    
    # Setup and run system tray
    setup_tray()
    icon_instance.run()

if __name__ == "__main__":
    main()
