import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import tempfile
import config
import shutil

class CyberButton(tk.Label):
    def __init__(self, master, text, command, bg, fg, hover_bg, font=None, **kwargs):
        font = font or ("Avenir Next", 14, "bold")
        super().__init__(master, text=text, bg=bg, fg=fg, font=font, cursor="hand2", **kwargs)
        self.bind("<Button-1>", lambda e: command())
        self.bind("<Enter>", lambda e: self.config(bg=hover_bg))
        self.bind("<Leave>", lambda e: self.config(bg=bg))

class SyncGUI(tk.Tk):
    def __init__(self, original_dir, modified_dir):
        super().__init__()
        self.original_dir = original_dir
        self.modified_dir = modified_dir
        self.title("Devbox: Sync Review")
        self.geometry("900x650")
        
        # Cyberpunk Cozy Global Settings
        self.bg_color = "#0D0814"
        self.panel_color = "#1A1025"
        self.fg_color = "#F0E6D2"
        self.accent_color = "#D9138A"
        self.accent_hover = "#FF3366"
        self.sub_accent = "#FF5722"
        self.sub_hover = "#FF8A65"
        self.font_title = ("Avenir Next", 22, "bold")
        self.font_sub = ("Avenir Next", 14)
        self.font_code = ("Menlo", 13)
        self.configure(bg=self.bg_color)
        
        # Force window to front using macOS AppleScript
        self.lift()
        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))
        os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
        
        self.config = config.load_config()
        self.changes = self.detect_changes()
        self.build_ui()
        
    def detect_changes(self):
        changes = []
        dlp_patterns = self.config.get("dlp_patterns", [])
        
        for root, dirs, files in os.walk(self.modified_dir):
            for f in files:
                mod_file = os.path.join(root, f)
                rel_path = os.path.relpath(mod_file, self.modified_dir)
                orig_file = os.path.join(self.original_dir, rel_path)
                
                is_dlp = False
                parts = rel_path.split(os.sep)
                for pattern in dlp_patterns:
                    if pattern in parts or f == pattern or (pattern.startswith('*') and f.endswith(pattern[1:])):
                        is_dlp = True
                        break
                    
                if not os.path.exists(orig_file):
                    changes.append({'path': rel_path, 'type': 'NEW', 'dlp': is_dlp})
                else:
                    if os.path.getsize(mod_file) != os.path.getsize(orig_file) or os.path.getmtime(mod_file) > os.path.getmtime(orig_file):
                        changes.append({'path': rel_path, 'type': 'MODIFIED', 'dlp': is_dlp})
        return changes
        
    def build_ui(self):
        # Header
        header_frame = tk.Frame(self, bg=self.bg_color)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(header_frame, text="Sandboxed Workspace Review", font=self.font_title, bg=self.bg_color, fg=self.accent_color).pack(anchor=tk.W)
        tk.Label(header_frame, text="Select the verified files you wish to securely sync back to your host machine.", font=self.font_sub, bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W, pady=2)
        
        # List Area
        list_container = tk.Frame(self, bg=self.panel_color, highlightbackground=self.accent_color, highlightthickness=1)
        list_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.canvas = tk.Canvas(list_container, bg=self.panel_color, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview, bg=self.panel_color)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.panel_color)
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=830)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.vars = {}
        if not self.changes:
            tk.Label(self.scrollable_frame, text="No modifications detected in the sandbox.", font=self.font_sub, bg=self.panel_color, fg="#888888").pack(pady=40)
            
        for c in self.changes:
            var = tk.BooleanVar(value=not c['dlp'])
            self.vars[c['path']] = var
            
            row = tk.Frame(self.scrollable_frame, bg=self.panel_color)
            row.pack(fill=tk.X, pady=6, padx=5)
            
            cb = tk.Checkbutton(row, variable=var, bg=self.panel_color, activebackground=self.panel_color, highlightthickness=0)
            cb.pack(side=tk.LEFT, padx=5)
            
            # Status Badge
            badge_color = "#FF3366" if c['dlp'] else ("#4CAF50" if c['type'] == 'NEW' else self.sub_accent)
            badge_text = "DLP FLAGGED" if c['dlp'] else c['type']
            badge = tk.Label(row, text=f" {badge_text} ", bg=badge_color, fg="#FFFFFF", font=("Avenir Next", 11, "bold"))
            badge.pack(side=tk.LEFT, padx=10)
            
            lbl = tk.Label(row, text=c['path'], bg=self.panel_color, fg=self.fg_color, font=self.font_code)
            lbl.pack(side=tk.LEFT)
            
            btn = CyberButton(row, text="View Diff", command=lambda item=c: self.view_diff(item), bg="#3B2651", fg="#FFFFFF", hover_bg="#573A75", font=("Avenir Next", 12, "bold"), padx=10, pady=4)
            btn.pack(side=tk.RIGHT, padx=10)
            
        # Footer
        footer_frame = tk.Frame(self, bg=self.bg_color)
        footer_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(footer_frame, text="Unchecked files will be vaporized permanently.", font=self.font_sub, bg=self.bg_color, fg="#888888").pack(side=tk.LEFT)
        
        sync_btn = CyberButton(footer_frame, text="Sync Selected Files", command=self.apply_sync, bg=self.accent_color, fg="#FFFFFF", hover_bg=self.accent_hover, padx=25, pady=10)
        sync_btn.pack(side=tk.RIGHT)
            
    def view_diff(self, c):
        orig_file = os.path.join(self.original_dir, c['path'])
        mod_file = os.path.join(self.modified_dir, c['path'])
        
        diff_lines = []
        if c['type'] == 'NEW':
            try:
                with open(mod_file, 'r', encoding='utf-8') as f:
                    diff_lines = [f"+ {line}" for line in f.read().splitlines(True)]
            except UnicodeDecodeError:
                diff_lines = ["<Binary File Added>"]
        elif c['type'] == 'MODIFIED':
            try:
                with open(orig_file, 'r', encoding='utf-8') as f1, open(mod_file, 'r', encoding='utf-8') as f2:
                    import difflib
                    diff_lines = list(difflib.unified_diff(
                        f1.readlines(), f2.readlines(),
                        fromfile=f"Host: {c['path']}", tofile=f"Jail: {c['path']}"
                    ))
            except UnicodeDecodeError:
                diff_lines = ["<Binary File Modified>"]
                
        # Diff Popup
        top = tk.Toplevel(self)
        top.title(f"Diff Viewer: {c['path']}")
        top.geometry("850x650")
        top.configure(bg=self.bg_color)
        
        # High Contrast Text Widget for Code
        text = tk.Text(top, wrap=tk.NONE, font=self.font_code, bg=self.panel_color, fg=self.fg_color, insertbackground="#FFFFFF", relief=tk.FLAT, padx=10, pady=10)
        yscroll = tk.Scrollbar(top, orient="vertical", command=text.yview, bg=self.panel_color)
        xscroll = tk.Scrollbar(top, orient="horizontal", command=text.xview, bg=self.panel_color)
        text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Syntax Highlighting Tags
        text.tag_configure("add", foreground="#00FF88")
        text.tag_configure("remove", foreground="#FF3366")
        text.tag_configure("header", foreground=self.accent_color)
        
        for line in diff_lines:
            tag = None
            if line.startswith('+') and not line.startswith('+++'):
                tag = "add"
            elif line.startswith('-') and not line.startswith('---'):
                tag = "remove"
            elif line.startswith('@@') or line.startswith('---') or line.startswith('+++'):
                tag = "header"
                
            text.insert(tk.END, line, tag)
            
        text.config(state=tk.DISABLED)
            
    def apply_sync(self):
        synced = 0
        for path, var in self.vars.items():
            if var.get():
                src = os.path.join(self.modified_dir, path)
                dst = os.path.join(self.original_dir, path)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                synced += 1
                
        success_dialog = tk.Toplevel(self)
        success_dialog.title("Success")
        success_dialog.geometry("300x150")
        success_dialog.configure(bg=self.bg_color)
        success_dialog.lift()
        success_dialog.attributes('-topmost', True)
        
        tk.Label(success_dialog, text=f"Successfully synced {synced} files!\n\nThe virtual jail has been vaporized.", font=self.font_sub, bg=self.bg_color, fg=self.fg_color).pack(expand=True)
        CyberButton(success_dialog, text="Close", command=self.destroy, bg=self.accent_color, fg="#FFFFFF", hover_bg=self.accent_hover).pack(pady=10)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(1)
    app = SyncGUI(sys.argv[1], sys.argv[2])
    app.mainloop()
