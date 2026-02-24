import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import traceback
import frequency_db

APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "MyTextExploder")
os.makedirs(APPDATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APPDATA_DIR, "config.json")
UI_ERROR_LOG = os.path.join(APPDATA_DIR, "ui_error.log")

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


def enable_window_drag(window, *widgets):
    """Allow dragging a window by clicking and dragging the supplied widgets."""
    drag_state = {"x": 0, "y": 0}

    def _start_drag(event):
        drag_state["x"] = event.x_root
        drag_state["y"] = event.y_root

    def _do_drag(event):
        dx = event.x_root - drag_state["x"]
        dy = event.y_root - drag_state["y"]
        drag_state["x"] = event.x_root
        drag_state["y"] = event.y_root
        x = window.winfo_x() + dx
        y = window.winfo_y() + dy
        window.geometry(f"+{x}+{y}")

    for widget in widgets:
        if widget is None:
            continue
        widget.bind("<ButtonPress-1>", _start_drag, add="+")
        widget.bind("<B1-Motion>", _do_drag, add="+")

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
    root.title("My Text Exploder — Settings")
    root.geometry("700x560")
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

    # Tab styling
    style.configure('TNotebook', background=THEME['bg'], borderwidth=0)
    style.configure('TNotebook.Tab',
                     background=THEME['input_bg'], foreground=THEME['fg'],
                     font=(THEME['font'], 10), padding=(16, 6))
    style.map('TNotebook.Tab',
              background=[('selected', THEME['bg'])],
              foreground=[('selected', THEME['accent'])])

    # ── Title section ──
    header_frame = ttk.Frame(root, style='TFrame')
    header_frame.pack(fill=tk.X, padx=20, pady=(16, 0))
    
    accent_bar = tk.Frame(header_frame, bg=THEME['accent'], width=3, height=22)
    accent_bar.pack(side=tk.LEFT, padx=(0, 10))
    
    title_label = ttk.Label(header_frame, text="My Text Exploder", style='Header.TLabel')
    title_label.pack(side=tk.LEFT)
    
    sub_label = ttk.Label(header_frame, text="Manage your text expansion shortcuts", style='Sub.TLabel')
    sub_label.pack(side=tk.LEFT, padx=(12, 0), pady=(3, 0))

    # Make the custom header area draggable (useful if the window loses native drag affordance/focus).
    enable_window_drag(root, header_frame, accent_bar, title_label, sub_label)

    # Divider
    tk.Frame(root, bg=THEME['border'], height=1).pack(fill=tk.X, padx=20, pady=(12, 0))

    # ── Notebook (tabs) ──
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(8, 0))

    config = load_config()

    # ════════════════════════════════════════════════════════
    #  TAB 1: SHORTCUTS (existing functionality)
    # ════════════════════════════════════════════════════════
    shortcuts_tab = ttk.Frame(notebook, style='TFrame')
    notebook.add(shortcuts_tab, text="  Shortcuts  ")

    # ── Treeview ──
    list_frame = ttk.Frame(shortcuts_tab, style='TFrame')
    list_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=(8, 0))

    columns = ('abbrev', 'replacement')
    tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='browse')
    tree.heading('abbrev', text='Abbreviation', anchor='w')
    tree.heading('replacement', text='Replacement Text', anchor='w')
    tree.column('abbrev', width=150, minwidth=100)
    tree.column('replacement', width=400, minwidth=200)
    
    scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    tree.pack(fill=tk.BOTH, expand=True)

    def populate_tree():
        for item in tree.get_children():
            tree.delete(item)
        for abbrev, repl in config.items():
            tree.insert('', tk.END, values=(abbrev, repl))

    populate_tree()

    # ── Input section ──
    tk.Frame(shortcuts_tab, bg=THEME['border'], height=1).pack(fill=tk.X, pady=(8, 0))
    
    control_frame = ttk.Frame(shortcuts_tab, style='TFrame')
    control_frame.pack(fill=tk.X, pady=(8, 0))

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
    btn_frame = ttk.Frame(shortcuts_tab, style='TFrame')
    btn_frame.pack(fill=tk.X, pady=(8, 8))
    
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
    
    count_label = ttk.Label(btn_frame, text=f"{len(config)} shortcut{'s' if len(config) != 1 else ''}", style='Sub.TLabel')
    count_label.pack(side=tk.RIGHT)

    # ════════════════════════════════════════════════════════
    #  TAB 2: SUGGESTIONS (frequency-based recommendations)
    # ════════════════════════════════════════════════════════
    suggestions_tab = ttk.Frame(notebook, style='TFrame')
    notebook.add(suggestions_tab, text="  Suggestions  ")

    # ── Header info ──
    sug_header = ttk.Frame(suggestions_tab, style='TFrame')
    sug_header.pack(fill=tk.X, pady=(8, 0))
    
    ttk.Label(
        sug_header,
        text="Words you type most often — promote them to shortcuts to save time.",
        style='Sub.TLabel'
    ).pack(side=tk.LEFT)
    
    stats_label = ttk.Label(sug_header, text="", style='Sub.TLabel')
    stats_label.pack(side=tk.RIGHT)

    # ── Suggestions Treeview ──
    sug_list_frame = ttk.Frame(suggestions_tab, style='TFrame')
    sug_list_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=(8, 0))

    sug_columns = ('phrase', 'count', 'last_typed')
    sug_tree = ttk.Treeview(sug_list_frame, columns=sug_columns, show='headings', selectmode='browse')
    sug_tree.heading('phrase', text='Phrase', anchor='w')
    sug_tree.heading('count', text='Times Typed', anchor='center')
    sug_tree.heading('last_typed', text='Last Typed', anchor='w')
    sug_tree.column('phrase', width=250, minwidth=150)
    sug_tree.column('count', width=100, minwidth=60, anchor='center')
    sug_tree.column('last_typed', width=200, minwidth=120)
    
    sug_scrollbar = ttk.Scrollbar(sug_list_frame, orient=tk.VERTICAL, command=sug_tree.yview)
    sug_tree.configure(yscrollcommand=sug_scrollbar.set)
    sug_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    sug_tree.pack(fill=tk.BOTH, expand=True)

    def refresh_suggestions():
        """Reload suggestions from the frequency database."""
        for item_id in sug_tree.get_children():
            sug_tree.delete(item_id)
        
        # Exclude phrases that are already config values (case-insensitive)
        existing_replacements = {v.lower() for v in config.values()}
        existing_abbrevs = {k.lower() for k in config.keys()}
        exclude = existing_replacements | existing_abbrevs
        
        try:
            suggestions = frequency_db.get_top_phrases(min_count=3, limit=20, exclude=exclude)
        except Exception:
            suggestions = []
        
        for sug in suggestions:
            # Format the last_typed timestamp nicely
            last = sug.get("last_typed", "")
            if "T" in last:
                last = last.split("T")[0]  # Just the date part
            sug_tree.insert('', tk.END, values=(sug["phrase"], sug["count"], last))
        
        # Update stats
        try:
            stats = frequency_db.get_phrase_stats()
            stats_label.config(
                text=f"{stats['total_phrases']} words tracked  ·  {stats['total_counts']} total keystrokes"
            )
        except Exception:
            stats_label.config(text="")

    def promote_suggestion():
        """Pre-fill the Shortcuts tab form with the selected suggestion."""
        selected = sug_tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Select a phrase to promote.")
            return
        item = sug_tree.item(selected[0])
        phrase = item['values'][0]
        
        # Switch to shortcuts tab and pre-fill the replacement
        notebook.select(shortcuts_tab)
        replacement_var.set(phrase)
        abbrev_var.set("")
        abbrev_entry.focus_set()

    def dismiss_suggestion():
        """Remove the selected phrase from frequency tracking."""
        selected = sug_tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Select a phrase to dismiss.")
            return
        item = sug_tree.item(selected[0])
        phrase = item['values'][0]
        
        frequency_db.dismiss_phrase(phrase)
        refresh_suggestions()

    # ── Suggestion buttons ──
    tk.Frame(suggestions_tab, bg=THEME['border'], height=1).pack(fill=tk.X, pady=(8, 0))
    
    sug_btn_frame = ttk.Frame(suggestions_tab, style='TFrame')
    sug_btn_frame.pack(fill=tk.X, pady=(8, 8))
    
    promote_btn = tk.Button(
        sug_btn_frame, text="⬆ Promote to Shortcut", command=promote_suggestion,
        bg=THEME['accent'], fg='white', activebackground=THEME['accent_hover'],
        activeforeground='white', font=(THEME['font'], 10, 'bold'),
        relief=tk.FLAT, padx=16, pady=6, cursor='hand2'
    )
    promote_btn.pack(side=tk.LEFT, padx=(0, 8))
    
    dismiss_btn = tk.Button(
        sug_btn_frame, text="✕ Dismiss", command=dismiss_suggestion,
        bg=THEME['bg'], fg='#dc2626', activebackground='#fef2f2',
        activeforeground='#dc2626', font=(THEME['font'], 10),
        relief=tk.SOLID, bd=1, padx=16, pady=6, cursor='hand2',
        highlightbackground='#fca5a5'
    )
    dismiss_btn.pack(side=tk.LEFT, padx=(0, 8))
    
    refresh_btn = tk.Button(
        sug_btn_frame, text="↻ Refresh", command=refresh_suggestions,
        bg=THEME['input_bg'], fg=THEME['fg'], activebackground=THEME['border'],
        activeforeground=THEME['fg'], font=(THEME['font'], 10),
        relief=tk.SOLID, bd=1, padx=16, pady=6, cursor='hand2',
        highlightbackground=THEME['input_border']
    )
    refresh_btn.pack(side=tk.LEFT)

    # ============================================================
    #  TAB 3: TRACKED (all tracked words/phrases)
    # ============================================================
    tracked_tab = ttk.Frame(notebook, style='TFrame')
    notebook.add(tracked_tab, text="  Tracked  ")

    tracked_header = ttk.Frame(tracked_tab, style='TFrame')
    tracked_header.pack(fill=tk.X, pady=(8, 0))

    ttk.Label(
        tracked_header,
        text="Everything currently stored in frequency tracking (most recent first).",
        style='Sub.TLabel'
    ).pack(side=tk.LEFT)

    tracked_stats_label = ttk.Label(tracked_header, text="", style='Sub.TLabel')
    tracked_stats_label.pack(side=tk.RIGHT)

    tracked_list_frame = ttk.Frame(tracked_tab, style='TFrame')
    tracked_list_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=(8, 0))

    tracked_columns = ('phrase', 'count', 'last_typed')
    tracked_tree = ttk.Treeview(tracked_list_frame, columns=tracked_columns, show='headings', selectmode='browse')
    tracked_tree.heading('phrase', text='Tracked Word / Phrase', anchor='w')
    tracked_tree.heading('count', text='Times Typed', anchor='center')
    tracked_tree.heading('last_typed', text='Last Typed', anchor='w')
    tracked_tree.column('phrase', width=320, minwidth=180)
    tracked_tree.column('count', width=100, minwidth=60, anchor='center')
    tracked_tree.column('last_typed', width=200, minwidth=120)

    tracked_scrollbar = ttk.Scrollbar(tracked_list_frame, orient=tk.VERTICAL, command=tracked_tree.yview)
    tracked_tree.configure(yscrollcommand=tracked_scrollbar.set)
    tracked_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    tracked_tree.pack(fill=tk.BOTH, expand=True)

    def refresh_tracked():
        for item_id in tracked_tree.get_children():
            tracked_tree.delete(item_id)
        try:
            tracked_rows = frequency_db.get_tracked_phrases(limit=500)
        except Exception:
            tracked_rows = []

        for row in tracked_rows:
            last = row.get("last_typed", "")
            if "T" in last:
                last = last.replace("T", " ")[:19]
            tracked_tree.insert('', tk.END, values=(row["phrase"], row["count"], last))

        try:
            stats = frequency_db.get_phrase_stats()
            tracked_stats_label.config(
                text=f"{stats['total_phrases']} tracked  ·  {stats['total_counts']} total"
            )
        except Exception:
            tracked_stats_label.config(text="")

    tk.Frame(tracked_tab, bg=THEME['border'], height=1).pack(fill=tk.X, pady=(8, 0))
    tracked_btn_frame = ttk.Frame(tracked_tab, style='TFrame')
    tracked_btn_frame.pack(fill=tk.X, pady=(8, 8))

    tracked_refresh_btn = tk.Button(
        tracked_btn_frame, text="Refresh", command=refresh_tracked,
        bg=THEME['input_bg'], fg=THEME['fg'], activebackground=THEME['border'],
        activeforeground=THEME['fg'], font=(THEME['font'], 10),
        relief=tk.SOLID, bd=1, padx=16, pady=6, cursor='hand2',
        highlightbackground=THEME['input_border']
    )
    tracked_refresh_btn.pack(side=tk.LEFT)

    # Load suggestions on tab switch
    def on_tab_change(event):
        selected_tab = notebook.index(notebook.select())
        if selected_tab == 1:  # Suggestions tab
            refresh_suggestions()
        elif selected_tab == 2:  # Tracked tab
            refresh_tracked()
    
    notebook.bind('<<NotebookTabChanged>>', on_tab_change)

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()

if __name__ == "__main__":
    try:
        open_settings_window(None)
    except Exception:
        with open(UI_ERROR_LOG, "a", encoding="utf-8") as f:
            f.write("\n=== ui.py crash ===\n")
            f.write(traceback.format_exc())
        raise
