"""
Quick test: Press Caps Lock a few times. This script logs what the
keyboard library sees so we can figure out the exact event name/scan code.
Runs for 15 seconds then writes results to _capslock_test.txt
"""
import keyboard, time, sys, os

log = []

def on_event(event):
    if event.event_type == 'down':
        log.append(f"name={event.name!r}  scan_code={event.scan_code}  is_keypad={event.is_keypad}")

print("Listening for 15 seconds — press Caps Lock a few times...")
sys.stdout.flush()
keyboard.hook(on_event)
time.sleep(15)
keyboard.unhook_all()

outpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_capslock_test.txt")
with open(outpath, "w", encoding="utf-8") as f:
    if log:
        for line in log:
            f.write(line + "\n")
    else:
        f.write("NO EVENTS CAPTURED\n")
print(f"Done — wrote {len(log)} events to _capslock_test.txt")
