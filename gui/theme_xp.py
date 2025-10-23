"""
Windows XP Blue Theme for tkinter/ttk
Recreates the classic Windows XP visual style with blue gradients and rounded elements
"""

import tkinter as tk
from tkinter import ttk


class XPColors:
    """Windows XP color palette"""
    # Main colors
    BLUE_GRADIENT_START = "#4A90E2"
    BLUE_GRADIENT_END = "#2171B5" 
    BLUE_ACCENT = "#316AC5"
    BLUE_HOVER = "#5B9BD5"
    
    # Backgrounds
    WINDOW_BG = "#ECE9D8"
    CONTROL_BG = "#F0F0F0" 
    WHITE = "#FFFFFF"
    
    # Text
    TEXT_BLACK = "#000000"
    TEXT_WHITE = "#FFFFFF"
    TEXT_DISABLED = "#808080"
    
    # Borders and shadows
    BORDER_DARK = "#808080"
    BORDER_LIGHT = "#E0E0E0"
    SHADOW = "#C0C0C0"


class XPTheme:
    """Applies Windows XP styling to ttk widgets"""
    
    def __init__(self, root):
        self.root = root
        self.style = ttk.Style()
        self._setup_theme()
        
    def _setup_theme(self):
        """Configure the XP theme"""
        # Set base theme
        try:
            self.style.theme_use('clam')  # Best base for customization
        except tk.TclError:
            self.style.theme_use('default')
            
        # Configure root window
        self.root.configure(bg=XPColors.WINDOW_BG)
        
        # Configure styles
        self._configure_notebook()
        self._configure_buttons()
        self._configure_labelframe()
        self._configure_entry()
        self._configure_combobox()
        self._configure_treeview()
        self._configure_scrollbar()
        
    def _configure_notebook(self):
        """Style notebook tabs with XP look"""
        self.style.configure(
            'TNotebook',
            background=XPColors.WINDOW_BG,
            borderwidth=1,
            relief='raised'
        )
        
        self.style.configure(
            'TNotebook.Tab',
            background=XPColors.CONTROL_BG,
            foreground=XPColors.TEXT_BLACK,
            padding=[12, 6],
            font=('Tahoma', 8, 'bold'),
            borderwidth=1,
            relief='raised',
            focuscolor='none'
        )
        
        self.style.map(
            'TNotebook.Tab',
            background=[
                ('selected', XPColors.WHITE),
                ('active', XPColors.BLUE_HOVER)
            ],
            foreground=[
                ('selected', XPColors.TEXT_BLACK),
                ('active', XPColors.TEXT_WHITE)
            ]
        )
        
    def _configure_buttons(self):
        """Style buttons with XP blue gradient"""
        self.style.configure(
            'XP.TButton',
            background=XPColors.BLUE_ACCENT,
            foreground=XPColors.TEXT_WHITE,
            font=('Tahoma', 8),
            padding=[8, 4],
            borderwidth=1,
            relief='raised',
            focuscolor='none'
        )
        
        self.style.map(
            'XP.TButton',
            background=[
                ('active', XPColors.BLUE_HOVER),
                ('pressed', XPColors.BLUE_GRADIENT_END)
            ],
            relief=[
                ('pressed', 'sunken'),
                ('active', 'raised')
            ]
        )
        
        # Regular buttons (less prominent)
        self.style.configure(
            'TButton',
            background=XPColors.CONTROL_BG,
            foreground=XPColors.TEXT_BLACK,
            font=('Tahoma', 8),
            padding=[6, 3],
            borderwidth=1,
            relief='raised',
            focuscolor='none'
        )
        
        self.style.map(
            'TButton',
            background=[
                ('active', XPColors.BORDER_LIGHT),
                ('pressed', XPColors.SHADOW)
            ]
        )
        
    def _configure_labelframe(self):
        """Style label frames with XP borders"""
        self.style.configure(
            'TLabelframe',
            background=XPColors.WINDOW_BG,
            borderwidth=2,
            relief='groove'
        )
        
        self.style.configure(
            'TLabelframe.Label',
            background=XPColors.WINDOW_BG,
            foreground=XPColors.TEXT_BLACK,
            font=('Tahoma', 8, 'bold')
        )
        
        # Special blue header style
        self.style.configure(
            'XPBlue.TLabelframe',
            background=XPColors.WINDOW_BG,
            borderwidth=2,
            relief='raised'
        )
        
        self.style.configure(
            'XPBlue.TLabelframe.Label',
            background=XPColors.BLUE_ACCENT,
            foreground=XPColors.TEXT_WHITE,
            font=('Tahoma', 8, 'bold'),
            padding=[8, 4]
        )
        
    def _configure_entry(self):
        """Style entry widgets"""
        self.style.configure(
            'TEntry',
            fieldbackground=XPColors.WHITE,
            background=XPColors.WHITE,
            foreground=XPColors.TEXT_BLACK,
            font=('Tahoma', 8),
            borderwidth=2,
            relief='sunken'
        )
        
    def _configure_combobox(self):
        """Style combobox widgets"""
        self.style.configure(
            'TCombobox',
            fieldbackground=XPColors.WHITE,
            background=XPColors.CONTROL_BG,
            foreground=XPColors.TEXT_BLACK,
            font=('Tahoma', 8),
            borderwidth=1,
            relief='sunken'
        )
        
    def _configure_treeview(self):
        """Style treeview/listbox"""
        self.style.configure(
            'Treeview',
            background=XPColors.WHITE,
            foreground=XPColors.TEXT_BLACK,
            font=('Tahoma', 8),
            borderwidth=1,
            relief='sunken'
        )
        
        self.style.configure(
            'Treeview.Heading',
            background=XPColors.BLUE_ACCENT,
            foreground=XPColors.TEXT_WHITE,
            font=('Tahoma', 8, 'bold'),
            relief='raised'
        )
        
    def _configure_scrollbar(self):
        """Style scrollbars"""
        self.style.configure(
            'TScrollbar',
            background=XPColors.CONTROL_BG,
            troughcolor=XPColors.WINDOW_BG,
            borderwidth=1,
            relief='sunken'
        )


class XPWidgets:
    """Custom XP-styled widgets"""
    
    @staticmethod
    def create_toolbar(parent, **kwargs):
        """Create XP-style toolbar"""
        toolbar = tk.Frame(
            parent,
            bg=XPColors.CONTROL_BG,
            relief='raised',
            bd=1,
            **kwargs
        )
        return toolbar
    
    @staticmethod 
    def create_status_bar(parent, **kwargs):
        """Create XP-style status bar"""
        statusbar = tk.Frame(
            parent,
            bg=XPColors.CONTROL_BG,
            relief='sunken',
            bd=1,
            **kwargs
        )
        return statusbar
    
    @staticmethod
    def create_panel(parent, title=None, **kwargs):
        """Create XP-style panel with optional blue header"""
        if title:
            frame = ttk.LabelFrame(
                parent, 
                text=title,
                style='XPBlue.TLabelframe',
                **kwargs
            )
        else:
            frame = tk.Frame(
                parent,
                bg=XPColors.WINDOW_BG,
                relief='groove',
                bd=2,
                **kwargs
            )
        return frame
    
    @staticmethod
    def create_button_group(parent, **kwargs):
        """Create button group container"""
        frame = tk.Frame(
            parent,
            bg=XPColors.WINDOW_BG,
            **kwargs
        )
        return frame


def apply_xp_theme(root):
    """Apply XP theme to root window"""
    theme = XPTheme(root)
    return theme

def get_xp_font(size=8, weight='normal'):
    """Get XP-style font"""
    return ('Tahoma', size, weight)