import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from main import CONFIG_FILE

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

def open_settings_window(reload_callback):
    root = tk.Tk()
    root.title("Text Exploder Settings")
    root.geometry("600x400")
    
    # Force window to foreground
    root.attributes('-topmost', True)
    root.after_idle(root.attributes, '-topmost', False)

    # Frame for list
    list_frame = ttk.Frame(root)
    list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    columns = ('abbrev', 'replacement')
    tree = ttk.Treeview(list_frame, columns=columns, show='headings')
    tree.heading('abbrev', text='Abbreviation')
    tree.heading('replacement', text='Replacement Text')
    tree.column('abbrev', width=150)
    tree.column('replacement', width=400)
    tree.pack(fill=tk.BOTH, expand=True)

    config = load_config()

    def populate_tree():
        for item in tree.get_children():
            tree.delete(item)
        for abbrev, repl in config.items():
            tree.insert('', tk.END, values=(abbrev, repl))

    populate_tree()

    # Frame for controls
    control_frame = ttk.Frame(root)
    control_frame.pack(fill=tk.X, padx=10, pady=10)

    ttk.Label(control_frame, text="Abbreviation:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
    abbrev_var = tk.StringVar()
    abbrev_entry = ttk.Entry(control_frame, textvariable=abbrev_var, width=20)
    abbrev_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

    ttk.Label(control_frame, text="Replacement:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
    replacement_var = tk.StringVar()
    replacement_entry = ttk.Entry(control_frame, textvariable=replacement_var, width=50)
    replacement_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

    def on_tree_select(event):
        selected = tree.selection()
        if selected:
            item = tree.item(selected[0])
            abbrev, repl = item['values']
            abbrev_var.set(abbrev)
            replacement_var.set(repl)

    tree.bind('<<TreeviewSelect>>', on_tree_select)

    def save_and_reload():
        save_config(config)
        populate_tree()
        if reload_callback:
            reload_callback()

    def add_update():
        abbrev = abbrev_var.get().strip()
        repl = replacement_var.get()
        if not abbrev or not repl:
            messagebox.showwarning("Input Error", "Both fields are required.")
            return
        
        config[abbrev] = repl
        save_and_reload()
        abbrev_var.set("")
        replacement_var.set("")

    def delete_item():
        abbrev = abbrev_var.get().strip()
        if abbrev in config:
            del config[abbrev]
            save_and_reload()
            abbrev_var.set("")
            replacement_var.set("")
        else:
            messagebox.showwarning("Not Found", "Abbreviation not found.")

    btn_frame = ttk.Frame(control_frame)
    btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

    ttk.Button(btn_frame, text="Add / Update", command=add_update).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Delete", command=delete_item).pack(side=tk.LEFT, padx=5)

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()

if __name__ == "__main__":
    open_settings_window(None)
