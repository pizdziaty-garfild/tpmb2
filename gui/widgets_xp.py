"""
Custom Windows XP widgets for TPMB2
Provides specialized XP-styled components matching the Groups reference design
"""

import tkinter as tk
from tkinter import ttk, messagebox
try:
    from .theme_xp import XPColors, get_xp_font
except ImportError:
    from theme_xp import XPColors, get_xp_font


class XPToolbar(tk.Frame):
    """Windows XP style toolbar with buttons"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=XPColors.CONTROL_BG, relief='raised', bd=1, **kwargs)
        self.buttons = {}
        
    def add_button(self, name, text, command=None, style='XP.TButton', **kwargs):
        """Add XP button to toolbar"""
        btn = ttk.Button(
            self, 
            text=text, 
            command=command, 
            style=style,
            **kwargs
        )
        btn.pack(side=tk.LEFT, padx=2, pady=2)
        self.buttons[name] = btn
        return btn
        
    def add_separator(self):
        """Add separator to toolbar"""
        sep = tk.Frame(self, bg=XPColors.BORDER_DARK, width=1, height=24)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)
        return sep
        
    def enable_button(self, name, enabled=True):
        """Enable/disable button"""
        if name in self.buttons:
            self.buttons[name].config(state=tk.NORMAL if enabled else tk.DISABLED)


class XPStatusBar(tk.Frame):
    """Windows XP style status bar"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=XPColors.CONTROL_BG, relief='sunken', bd=1, **kwargs)
        self.labels = {}
        
    def add_field(self, name, text="", width=None):
        """Add status field"""
        if width:
            label = tk.Label(
                self, 
                text=text, 
                bg=XPColors.CONTROL_BG,
                fg=XPColors.TEXT_BLACK,
                font=get_xp_font(),
                width=width,
                anchor='w',
                relief='sunken',
                bd=1
            )
        else:
            label = tk.Label(
                self, 
                text=text, 
                bg=XPColors.CONTROL_BG,
                fg=XPColors.TEXT_BLACK,
                font=get_xp_font(),
                anchor='w'
            )
        label.pack(side=tk.LEFT, fill=tk.X, expand=True if width is None else False, padx=1, pady=1)
        self.labels[name] = label
        return label
        
    def update_field(self, name, text):
        """Update status field text"""
        if name in self.labels:
            self.labels[name].config(text=text)


class XPListView(tk.Frame):
    """Windows XP style list view with icons"""
    
    def __init__(self, parent, columns=None, **kwargs):
        super().__init__(parent, bg=XPColors.WHITE, relief='sunken', bd=2, **kwargs)
        
        # Create treeview
        if columns:
            self.tree = ttk.Treeview(self, columns=columns, show='tree headings')
        else:
            self.tree = ttk.Treeview(self, show='tree')
            
        # Scrollbars
        v_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Pack widgets
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Configure columns
        if columns:
            for col in columns:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=100)
                
    def add_item(self, text, values=None, **kwargs):
        """Add item to list"""
        return self.tree.insert('', tk.END, text=text, values=values or [], **kwargs)
        
    def clear(self):
        """Clear all items"""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
    def get_selection(self):
        """Get selected items"""
        return self.tree.selection()
        
    def bind_double_click(self, callback):
        """Bind double-click event"""
        self.tree.bind('<Double-1>', callback)


class XPPopupWindow(tk.Toplevel):
    """XP-styled popup window"""
    
    def __init__(self, parent, title="", width=400, height=300, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.configure(bg=XPColors.WINDOW_BG)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")
        
        # Header with blue background
        self.header_frame = tk.Frame(self, bg=XPColors.BLUE_ACCENT, height=32)
        self.header_frame.pack(fill=tk.X)
        self.header_frame.pack_propagate(False)
        
        self.title_label = tk.Label(
            self.header_frame,
            text=title,
            bg=XPColors.BLUE_ACCENT,
            fg=XPColors.TEXT_WHITE,
            font=get_xp_font(size=9, weight='bold')
        )
        self.title_label.pack(side=tk.LEFT, padx=8, pady=6)
        
        # Close button
        self.close_btn = tk.Label(
            self.header_frame,
            text="X",
            bg=XPColors.BLUE_ACCENT,
            fg=XPColors.TEXT_WHITE,
            font=get_xp_font(size=10, weight='bold'),
            cursor='hand2'
        )
        self.close_btn.pack(side=tk.RIGHT, padx=8, pady=6)
        self.close_btn.bind('<Button-1>', lambda e: self.destroy())
        
        # Content area
        self.content_frame = tk.Frame(self, bg=XPColors.WINDOW_BG)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)