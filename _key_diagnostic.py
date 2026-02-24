"""Diagnostic: press Caps Lock to see what name the keyboard library reports."""
import keyboard
import time
import sys

print("Press Caps Lock (or any key) within 10 seconds...")
print("Will log all KEY_DOWN events.\n")
sys.stdout.flush()

results = []

def on_event(event):
    if event.event_type == 'down':
        line = f"name={event.name!r}  scan_code={event.scan_code}  event_type={event.event_type}"
        results.append(line)

keyboard.hook(on_event)
time.sleep(10)
keyboard.unhook_all()

# Write results to file
with open("_key_diagnostic.txt", "w") as f:
    for r in results:
        f.write(r + "\n")
    if not results:
        f.write("No key events captured.\n")

print("Done. Results written to _key_diagnostic.txt")
