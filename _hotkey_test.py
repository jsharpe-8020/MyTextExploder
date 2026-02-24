import keyboard
import time
import tkinter as tk
from tkinter import messagebox
import sys

def on_hotkey():
    print("Hotkey triggered!")
    root = tk.Tk()
    root.withdraw() # Hide main window
    messagebox.showinfo("Hotkey Test", "The hotkey was successfully triggered!")
    root.destroy()
    sys.exit(0)

print("Listening for Ctrl+Shift+Alt...")
keyboard.add_hotkey('ctrl+shift+alt', on_hotkey, suppress=False)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
