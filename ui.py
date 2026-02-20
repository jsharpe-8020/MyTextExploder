import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from main import CONFIG_FILE

# BuildOps-inspired theme: white dominant, green (#00AF66) highlight
THEME = {
    'bg': '#FFFFFF',
    'fg': '#1a1a1a',
    'fg_secondary': '#6b7280',
    'accent': '#00AF66',
    'accent_hover': '#009957',
    'border': '#e5e7eb',
    'input_bg': '#f9fafb',
    'input_border': '#d1d5db',
    'font': 'Segoe UI',
    'mono': 'Cascadia Code',
}

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
    root.title("Text Exploder — Settings")
    root.geometry("640x480")
    root.config(bg=THEME['bg'])
    root.resizable(True, True)
    
    # Force window to foreground
    root.attributes('-topmost', True)
    root.after_idle(root.attributes, '-topmost', False)

    # ── Custom ttk styling ──
    style = ttk.Style()
    style.theme_use('clam')
    
    style.configure('TFrame', background=THEME['bg'])
    style.configure('TLabel', background=THEME['bg'], foreground=THEME['fg'], font=(THEME['font'], 10))
    style.configure('Header.TLabel', background=THEME['bg'], foreground=THEME['fg'], font=(THEME['font'], 14, 'bold'))
    style.configure('Sub.TLabel', background=THEME['bg'], foreground=THEME['fg_secondary'], font=(THEME['font'], 9))
    
    style.configure('TEntry', fieldbackground=THEME['input_bg'], foreground=THEME['fg'],
                     font=(THEME['font'], 10), borderwidth=1, relief='solid')
    
    style.configure('Accent.TButton',
                     background=THEME['accent'], foreground='white',
                     font=(THEME['font'], 10, 'bold'),
                     borderwidth=0, padding=(16, 8))
    style.map('Accent.TButton',
              background=[('active', THEME['accent_hover']), ('pressed', THEME['accent_hover'])])
    
    style.configure('Outline.TButton',
                     background=THEME['bg'], foreground=THEME['fg'],
                     font=(THEME['font'], 10),
                     borderwidth=1, padding=(16, 8))
    style.map('Outline.TButton',
              background=[('active', '#fef2f2')])
    
    style.configure('Treeview',
                     background=THEME['bg'], foreground=THEME['fg'],
                     fieldbackground=THEME['bg'],
                     font=(THEME['mono'], 10),
                     rowheight=28, borderwidth=0)
    style.configure('Treeview.Heading',
                     background=THEME['input_bg'], foreground=THEME['fg'],
                     font=(THEME['font'], 10, 'bold'),
                     borderwidth=0, relief='flat')
    style.map('Treeview',
              background=[('selected', THEME['accent'])],
              foreground=[('selected', 'white')])

    # ── Title section ──
    header_frame = ttk.Frame(root, style='TFrame')
    header_frame.pack(fill=tk.X, padx=20, pady=(16, 0))
    
    accent_bar = tk.Frame(header_frame, bg=THEME['accent'], width=3, height=22)
    accent_bar.pack(side=tk.LEFT, padx=(0, 10))
    
    title_label = ttk.Label(header_frame, text="Text Exploder", style='Header.TLabel')
    title_label.pack(side=tk.LEFT)
    
    sub_label = ttk.Label(header_frame, text="Manage your text expansion shortcuts", style='Sub.TLabel')
    sub_label.pack(side=tk.LEFT, padx=(12, 0), pady=(3, 0))

    # Divider
    tk.Frame(root, bg=THEME['border'], height=1).pack(fill=tk.X, padx=20, pady=(12, 0))

    # ── Treeview ──
    list_frame = ttk.Frame(root, style='TFrame')
    list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(12, 0))

    columns = ('abbrev', 'replacement')
    tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='browse')
    tree.heading('abbrev', text='Abbreviation', anchor='w')
    tree.heading('replacement', text='Replacement Text', anchor='w')
    tree.column('abbrev', width=150, minwidth=100)
    tree.column('replacement', width=400, minwidth=200)
    
    # Scrollbar
    scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    tree.pack(fill=tk.BOTH, expand=True)

    config = load_config()

    def populate_tree():
        for item in tree.get_children():
            tree.delete(item)
        for abbrev, repl in config.items():
            tree.insert('', tk.END, values=(abbrev, repl))

    populate_tree()

    # Divider
    tk.Frame(root, bg=THEME['border'], height=1).pack(fill=tk.X, padx=20, pady=(12, 0))

    # ── Input section ──
    control_frame = ttk.Frame(root, style='TFrame')
    control_frame.pack(fill=tk.X, padx=20, pady=(12, 0))

    ttk.Label(control_frame, text="Abbreviation").grid(row=0, column=0, padx=(0, 8), pady=4, sticky=tk.W)
    abbrev_var = tk.StringVar()
    abbrev_entry = tk.Entry(
        control_frame, textvariable=abbrev_var, width=20,
        relief=tk.SOLID, bd=1, bg=THEME['input_bg'], fg=THEME['fg'],
        font=(THEME['font'], 10), insertbackground=THEME['accent'],
        highlightthickness=1, highlightcolor=THEME['accent'], highlightbackground=THEME['input_border']
    )
    abbrev_entry.grid(row=0, column=1, padx=(0, 16), pady=4, sticky=tk.W)

    ttk.Label(control_frame, text="Replacement").grid(row=0, column=2, padx=(0, 8), pady=4, sticky=tk.W)
    replacement_var = tk.StringVar()
    replacement_entry = tk.Entry(
        control_frame, textvariable=replacement_var, width=35,
        relief=tk.SOLID, bd=1, bg=THEME['input_bg'], fg=THEME['fg'],
        font=(THEME['font'], 10), insertbackground=THEME['accent'],
        highlightthickness=1, highlightcolor=THEME['accent'], highlightbackground=THEME['input_border']
    )
    replacement_entry.grid(row=0, column=3, pady=4, sticky=tk.EW)
    control_frame.columnconfigure(3, weight=1)

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

    # ── Buttons ──
    btn_frame = ttk.Frame(root, style='TFrame')
    btn_frame.pack(fill=tk.X, padx=20, pady=(12, 16))
    
    add_btn = tk.Button(
        btn_frame, text="Add / Update", command=add_update,
        bg=THEME['accent'], fg='white', activebackground=THEME['accent_hover'],
        activeforeground='white', font=(THEME['font'], 10, 'bold'),
        relief=tk.FLAT, padx=16, pady=6, cursor='hand2'
    )
    add_btn.pack(side=tk.LEFT, padx=(0, 8))
    
    del_btn = tk.Button(
        btn_frame, text="Delete", command=delete_item,
        bg=THEME['bg'], fg='#dc2626', activebackground='#fef2f2',
        activeforeground='#dc2626', font=(THEME['font'], 10),
        relief=tk.SOLID, bd=1, padx=16, pady=6, cursor='hand2',
        highlightbackground='#fca5a5'
    )
    del_btn.pack(side=tk.LEFT)
    
    # Item count on right
    count_label = ttk.Label(btn_frame, text=f"{len(config)} shortcut{'s' if len(config) != 1 else ''}", style='Sub.TLabel')
    count_label.pack(side=tk.RIGHT)

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()

if __name__ == "__main__":
    open_settings_window(None)
