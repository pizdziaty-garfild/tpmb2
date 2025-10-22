#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TPMB2 - Enhanced Telegram Periodic Message Bot v2.1 - Multi-Bot Edition
Main GUI application with comprehensive error handling, diagnostics, and multi-bot licensing
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import threading
import asyncio
import tempfile
import zipfile
import io
import json
import ssl
import traceback
import logging
from urllib.request import urlopen, Request
from datetime import datetime

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def ensure_logs_directory():
    """Ensure logs directory exists"""
    logs_dir = os.path.join(current_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

def log_startup_error(error_msg, tb_str):
    """Log startup errors to file"""
    logs_dir = ensure_logs_directory()
    error_file = os.path.join(logs_dir, 'error-startup.log')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(error_file, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"STARTUP ERROR: {timestamp}\n")
        f.write(f"Error: {error_msg}\n")
        f.write(f"Traceback:\n{tb_str}\n")
        f.write(f"{'='*60}\n")

def check_requirements():
    """Check if all required modules are available with detailed reporting"""
    required = [
        ('telegram', 'python-telegram-bot>=20.7'),
        ('cryptography', 'cryptography>=41.0.0'), 
        ('ssl', 'built-in (should be available)'),
        ('tkinter', 'built-in GUI (should be available)'),
        ('requests', 'requests>=2.31.0'),
        ('certifi', 'certifi>=2023.7.22'),
        ('ntplib', 'ntplib>=0.4.0')
    ]
    
    optional = [
        ('aiohttp', 'aiohttp>=3.9.0 (for proxy support)'),
        ('aiohttp_socks', 'aiohttp-socks>=0.8.4 (for SOCKS5 proxy)')
    ]
    
    missing_critical = []
    missing_optional = []
    
    # Check critical dependencies
    for module, package in required:
        try:
            __import__(module)
        except ImportError:
            missing_critical.append(package)
    
    # Check optional dependencies
    for module, package in optional:
        try:
            __import__(module)
        except ImportError:
            missing_optional.append(package)
    
    if missing_critical:
        error_msg = f"""Missing critical dependencies:
{chr(10).join('• ' + pkg for pkg in missing_critical)}

Install with:
python -m pip install {' '.join(pkg.split('>=')[0] for pkg in missing_critical)}

Then restart the application."""
        messagebox.showerror("Missing Dependencies", error_msg)
        return False
    
    if missing_optional:
        warning_msg = f"""Optional dependencies missing:
{chr(10).join('• ' + pkg for pkg in missing_optional)}

Some features (SOCKS5 proxy) may not work.
Install with:
python -m pip install {' '.join(pkg.split('>=')[0] for pkg in missing_optional)}

Continue anyway?"""
        if not messagebox.askyesno("Optional Dependencies", warning_msg):
            return False
    
    return True

class LicenseDialog:
    def __init__(self, parent):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Generate License Key")
        self.dialog.geometry("500x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self._create_widgets()
        
    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🔑 TPMB2 License Generator", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0,15))
        
        # Bot name input
        ttk.Label(main_frame, text="Bot Name (for reference):").pack(anchor=tk.W, pady=(0,5))
        self.bot_name_var = tk.StringVar(value="My Bot")
        ttk.Entry(main_frame, textvariable=self.bot_name_var, width=40).pack(fill=tk.X, pady=(0,15))
        
        # Days valid
        ttk.Label(main_frame, text="License validity (days):").pack(anchor=tk.W, pady=(0,5))
        self.days_var = tk.StringVar(value="365")
        ttk.Entry(main_frame, textvariable=self.days_var, width=10).pack(anchor=tk.W, pady=(0,15))
        
        # Hardware lock
        self.hw_lock_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="Hardware lock (bind to this computer)", variable=self.hw_lock_var).pack(anchor=tk.W, pady=(0,15))
        
        # Generate button
        ttk.Button(main_frame, text="🎯 Generate License Key", command=self._generate_key).pack(pady=(0,15))
        
        # Result area
        ttk.Label(main_frame, text="Generated License Key:").pack(anchor=tk.W, pady=(0,5))
        self.result_text = scrolledtext.ScrolledText(main_frame, height=4, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True, pady=(0,15))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        ttk.Button(button_frame, text="Copy Key", command=self._copy_key).pack(side=tk.LEFT, padx=(0,10))
        ttk.Button(button_frame, text="Close", command=self._close).pack(side=tk.RIGHT)
        
    def _generate_key(self):
        try:
            from utils.licensing import LicenseManager
            from utils.config import Config
            
            days = int(self.days_var.get())
            if days < 1:
                raise ValueError("Days must be > 0")
                
            config = Config()
            token = config.get_bot_token()
            if not token:
                messagebox.showerror("Error", "No bot token configured! Set token first in Configuration.")
                return
                
            lm = LicenseManager()
            hwid = lm.get_hwid() if self.hw_lock_var.get() else None
            
            key = lm.generate_key(bot_token=token, days_valid=days, hwid=hwid)
            
            result = f"""License Key: {key}

Bot Name: {self.bot_name_var.get()}
Valid for: {days} days
Hardware Lock: {'Yes' if hwid else 'No'}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ Keep this key secure - it grants access to your bot!
"""
            
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', result)
            self.result = key
            
        except Exception as e:
            messagebox.showerror("Generation Error", f"Failed to generate license: {e}")
    
    def _copy_key(self):
        if self.result:
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(self.result)
            messagebox.showinfo("Copied", "License key copied to clipboard!")
    
    def _close(self):
        self.dialog.destroy()

class GroupEditDialog:
    def __init__(self, parent, group_id, group_name="", group_interval=None):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Group")
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Variables
        self.name_var = tk.StringVar(value=group_name or "")
        self.interval_var = tk.StringVar(value=str(group_interval) if group_interval else "")
        
        self._create_widgets(group_id)
        
    def _create_widgets(self, group_id):
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Group ID (read-only)
        ttk.Label(main_frame, text="Group ID:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(main_frame, text=str(group_id), font=('Arial', 9, 'bold')).grid(row=0, column=1, sticky=tk.W, padx=(10,0))
        
        # Name
        ttk.Label(main_frame, text="Name (optional):").grid(row=1, column=0, sticky=tk.W, pady=2)
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=30)
        name_entry.grid(row=1, column=1, sticky=tk.EW, padx=(10,0), pady=2)
        
        # Interval
        ttk.Label(main_frame, text="Interval (min, empty=global):").grid(row=2, column=0, sticky=tk.W, pady=2)
        interval_entry = ttk.Entry(main_frame, textvariable=self.interval_var, width=10)
        interval_entry.grid(row=2, column=1, sticky=tk.W, padx=(10,0), pady=2)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(20,0))
        ttk.Button(button_frame, text="Save", command=self._save).pack(side=tk.LEFT, padx=(0,10))
        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side=tk.LEFT)
        
        main_frame.columnconfigure(1, weight=1)
        name_entry.focus()
        
    def _save(self):
        name = self.name_var.get().strip() or None
        interval_str = self.interval_var.get().strip()
        interval = None
        if interval_str:
            try:
                interval = int(interval_str)
                if interval < 1:
                    raise ValueError("Must be >= 1")
            except ValueError:
                messagebox.showerror("Error", "Interval must be a positive number or empty")
                return
        
        self.result = (name, interval)
        self.dialog.destroy()
        
    def _cancel(self):
        self.result = None
        self.dialog.destroy()

class TPMB2GUI:
    def __init__(self):
        try:
            if not check_requirements():
                sys.exit(1)
            
            # Import after requirements check
            from bot.core import TelegramBot
            from utils.config import Config
            from utils.logger import setup_logger
            from utils.bots_registry import BotRegistry
            from utils.licensing import LicenseManager
            
            self.root = tk.Tk()
            self.root.title("TPMB2 - Enhanced Bot Manager v2.1 - Multi-Bot Edition")
            self.root.geometry("1100x800")
            self.root.minsize(900, 650)
            
            self.bot = None
            self.config = Config()
            self.registry = BotRegistry()
            self.licenser = LicenseManager()
            self.logger = setup_logger()
            self.bot_thread = None
            self.is_running = False
            
            self._create_ui()
            self._update_status()
            self.root.after(2000, self._periodic_update)
            
            # Log successful startup
            self.logger.info("TPMB2 GUI initialized successfully")
            
        except Exception as e:
            # Critical startup error handling
            tb_str = traceback.format_exc()
            error_msg = f"Failed to initialize TPMB2 GUI: {str(e)}"
            log_startup_error(error_msg, tb_str)
            
            # Show error dialog with details
            error_dialog = f"""{error_msg}

Details logged to logs/error-startup.log

Technical details:
{tb_str[-500:]}"""
            
            try:
                messagebox.showerror("TPMB2 Startup Error", error_dialog)
            except:
                # If even messagebox fails, print to console
                print(f"CRITICAL ERROR: {error_msg}")
                print(tb_str)
            
            sys.exit(1)
    
    def _create_ui(self):
        try:
            # Menu bar
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            
            file_menu = tk.Menu(menubar, tearoff=0)
            file_menu.add_command(label="Update from GitHub", command=self._safe_update_from_github)
            file_menu.add_separator()
            file_menu.add_command(label="Exit", command=self._on_close)
            menubar.add_cascade(label="File", menu=file_menu)
            
            bot_menu = tk.Menu(menubar, tearoff=0)
            bot_menu.add_command(label="Start Bot", command=self._start_bot)
            bot_menu.add_command(label="Restart Bot", command=self._restart_bot)
            bot_menu.add_command(label="Stop Bot", command=self._stop_bot)
            menubar.add_cascade(label="Bot", menu=bot_menu)
            
            # Status frame with license indicator
            status_frame = ttk.LabelFrame(self.root, text="Status", padding=10)
            status_frame.pack(fill=tk.X, padx=10, pady=5)
            
            self.status_var = tk.StringVar(value="Stopped")
            self.groups_var = tk.StringVar(value="0")
            self.license_var = tk.StringVar(value="❌ No License")
            self.interval_var = tk.StringVar(value=str(self.config.get_interval_minutes()))
            
            ttk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky=tk.W)
            self.status_label = ttk.Label(status_frame, textvariable=self.status_var, font=('Arial', 9, 'bold'))
            self.status_label.grid(row=0, column=1, sticky=tk.W, padx=(5,20))
            
            ttk.Label(status_frame, text="Groups:").grid(row=0, column=2, sticky=tk.W)
            ttk.Label(status_frame, textvariable=self.groups_var).grid(row=0, column=3, sticky=tk.W, padx=(5,20))
            
            ttk.Label(status_frame, text="License:").grid(row=0, column=4, sticky=tk.W)
            self.license_label = ttk.Label(status_frame, textvariable=self.license_var, font=('Arial', 8))
            self.license_label.grid(row=0, column=5, sticky=tk.W, padx=(5,0))
            
            # Control frame
            ctrl_frame = ttk.LabelFrame(self.root, text="Control", padding=10)
            ctrl_frame.pack(fill=tk.X, padx=10, pady=5)
            
            self.start_btn = ttk.Button(ctrl_frame, text="Start Bot", command=self._start_bot)
            self.start_btn.grid(row=0, column=0, padx=(0,5))
            
            self.restart_btn = ttk.Button(ctrl_frame, text="Restart Bot", command=self._restart_bot, state=tk.DISABLED)
            self.restart_btn.grid(row=0, column=1, padx=5)
            
            self.stop_btn = ttk.Button(ctrl_frame, text="Stop Bot", command=self._stop_bot, state=tk.DISABLED)
            self.stop_btn.grid(row=0, column=2, padx=5)
            
            ttk.Label(ctrl_frame, text="Global Interval (min):").grid(row=0, column=3, padx=(20,5))
            interval_entry = ttk.Entry(ctrl_frame, textvariable=self.interval_var, width=5)
            interval_entry.grid(row=0, column=4)
            interval_entry.bind('<Return>', self._update_interval)
            ttk.Button(ctrl_frame, text="Apply", command=self._update_interval).grid(row=0, column=5, padx=(5,0))
            
            # Notebook for tabs
            notebook = ttk.Notebook(self.root)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Configuration tab
            config_tab = ttk.Frame(notebook)
            notebook.add(config_tab, text="Configuration")
            self._create_config_tab(config_tab)
            
            # Bot Management tab (NEW!)
            bot_mgmt_tab = ttk.Frame(notebook)
            notebook.add(bot_mgmt_tab, text="Bot Management")
            self._create_bot_management_tab(bot_mgmt_tab)
            
            # Logs tab
            logs_tab = ttk.Frame(notebook)
            notebook.add(logs_tab, text="Logs")
            self._create_logs_tab(logs_tab)
            
            # Groups tab
            groups_tab = ttk.Frame(notebook)
            notebook.add(groups_tab, text="Groups")
            self._create_groups_tab(groups_tab)
            
        except Exception as e:
            self.logger.exception("Error creating UI")
            messagebox.showerror("UI Error", f"Failed to create user interface: {e}")
            raise
    
    def _create_bot_management_tab(self, parent):
        """NEW: Bot Management tab with multi-bot and licensing features"""
        try:
            parent.columnconfigure(1, weight=1)
            
            # Active Bot Selection
            active_frame = ttk.LabelFrame(parent, text="🤖 Active Bot Selection", padding=10)
            active_frame.grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=(0,10))
            active_frame.columnconfigure(1, weight=1)
            
            ttk.Label(active_frame, text="Active Bot:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.active_bot_var = tk.StringVar()
            self.bot_combo = ttk.Combobox(active_frame, textvariable=self.active_bot_var, state="readonly", width=40)
            self.bot_combo.grid(row=0, column=1, sticky=tk.EW, padx=(10,0), pady=2)
            self.bot_combo.bind('<<ComboboxSelected>>', self._on_bot_selected)
            
            bot_buttons_frame = ttk.Frame(active_frame)
            bot_buttons_frame.grid(row=0, column=2, padx=(10,0))
            ttk.Button(bot_buttons_frame, text="Set Active", command=self._set_active_bot).pack(side=tk.LEFT, padx=(0,5))
            ttk.Button(bot_buttons_frame, text="Add Bot", command=self._add_bot).pack(side=tk.LEFT, padx=5)
            ttk.Button(bot_buttons_frame, text="Remove", command=self._remove_bot).pack(side=tk.LEFT, padx=5)
            
            # License Management
            license_frame = ttk.LabelFrame(parent, text="🔑 License Management", padding=10)
            license_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=(0,10))
            license_frame.columnconfigure(1, weight=1)
            
            ttk.Label(license_frame, text="License Key:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.license_key_var = tk.StringVar()
            ttk.Entry(license_frame, textvariable=self.license_key_var, width=50, font=('Consolas', 9)).grid(row=0, column=1, sticky=tk.EW, padx=(10,0), pady=2)
            
            license_buttons_frame = ttk.Frame(license_frame)
            license_buttons_frame.grid(row=0, column=2, padx=(10,0))
            ttk.Button(license_buttons_frame, text="Validate", command=self._validate_license).pack(side=tk.LEFT, padx=(0,5))
            ttk.Button(license_buttons_frame, text="Activate", command=self._activate_license).pack(side=tk.LEFT, padx=5)
            
            # License Status
            ttk.Label(license_frame, text="Status:").grid(row=1, column=0, sticky=tk.W, pady=(10,2))
            self.license_status_var = tk.StringVar(value="No license configured")
            self.license_status_label = ttk.Label(license_frame, textvariable=self.license_status_var, font=('Arial', 9))
            self.license_status_label.grid(row=1, column=1, sticky=tk.W, padx=(10,0), pady=(10,2))
            
            # License Tools
            tools_frame = ttk.LabelFrame(parent, text="🛠️ License Tools", padding=10)
            tools_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=(0,10))
            
            ttk.Button(tools_frame, text="🎯 Generate License Key", command=self._generate_license).pack(side=tk.LEFT, padx=(0,10))
            ttk.Button(tools_frame, text="📋 Check HWID", command=self._show_hwid).pack(side=tk.LEFT, padx=10)
            ttk.Button(tools_frame, text="📊 License Info", command=self._show_license_info).pack(side=tk.LEFT, padx=10)
            
            # Bot Info Display
            info_frame = ttk.LabelFrame(parent, text="📄 Bot Information", padding=10)
            info_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.EW, tk.NS), padx=10, pady=(0,10))
            info_frame.columnconfigure(0, weight=1)
            info_frame.rowconfigure(0, weight=1)
            
            self.bot_info_text = scrolledtext.ScrolledText(info_frame, height=8, wrap=tk.WORD, font=('Consolas', 9))
            self.bot_info_text.pack(fill=tk.BOTH, expand=True)
            
            # Initialize bot list
            self._refresh_bot_list()
            
        except Exception as e:
            self.logger.exception("Error creating bot management tab")
            messagebox.showerror("Bot Management Error", f"Failed to create bot management tab: {e}")
    
    def _refresh_bot_list(self):
        """Refresh the bot list in the combo box"""
        try:
            bots = self.registry.list_bots()
            active_bot = self.registry.get_active_bot()
            
            # Add default entry if no bots exist
            if not bots:
                bots = ["(create first bot)"]
                display_bots = bots
            else:
                # Add license status indicators
                display_bots = []
                for bot_id in bots:
                    bot_data = self.registry.get_bot(bot_id)
                    name = bot_data.get('name', bot_id)
                    status = bot_data.get('license_status', 'inactive')
                    
                    if status == 'active':
                        indicator = "✅"
                    elif 'expired' in status or 'invalid' in status:
                        indicator = "⚠️"
                    else:
                        indicator = "❌"
                    
                    display_bots.append(f"{indicator} {name} ({bot_id})")
            
            self.bot_combo['values'] = display_bots
            
            # Set current selection
            if active_bot and active_bot in bots:
                for i, bot_id in enumerate(bots):
                    if bot_id == active_bot:
                        self.bot_combo.current(i)
                        break
            elif display_bots:
                self.bot_combo.current(0)
            
            self._update_bot_info()
            
        except Exception as e:
            self.logger.exception("Error refreshing bot list")
    
    def _update_bot_info(self):
        """Update bot info display"""
        try:
            active_bot = self.registry.get_active_bot()
            
            if not active_bot:
                info = "No active bot selected.\n\n1. Click 'Add Bot' to create your first bot\n2. Set license key\n3. Set as active"
                self.bot_info_text.delete('1.0', tk.END)
                self.bot_info_text.insert('1.0', info)
                return
                
            bot_data = self.registry.get_bot(active_bot)
            token = self.config.get_bot_token()
            
            # Get license validation
            license_key = bot_data.get('license_key', '')
            license_status = "No license"
            license_details = ""
            
            if license_key:
                try:
                    status = self.licenser.validate_key(license_key, bot_token=token or "DUMMY", hwid=self.licenser.get_hwid())
                    if status.get('valid'):
                        license_status = f"✅ Active (expires: 20{status.get('expires', 'XX')})"
                    else:
                        license_status = f"❌ Invalid ({status.get('reason', 'unknown')})"
                        license_details = f"Reason: {status.get('reason', 'N/A')}"
                except Exception as e:
                    license_status = f"❌ Error: {str(e)[:50]}"
            
            info = f"""Bot ID: {active_bot}
Name: {bot_data.get('name', 'Unnamed')}
Created: {bot_data.get('created_date', 'Unknown')}

License Status: {license_status}
{license_details}

License Key: {license_key[:20] + '...' if license_key else 'Not set'}

Groups Count: {len(self.config.get_groups())}
Templates Count: {len(self.config.list_templates())}
Active Template: {self.config.get_active_template_key()}

Bot Token: {'Configured' if token else 'Not set'}
"""
            
            self.bot_info_text.delete('1.0', tk.END)
            self.bot_info_text.insert('1.0', info)
            
        except Exception as e:
            self.logger.exception("Error updating bot info")
    
    def _on_bot_selected(self, event=None):
        """Handle bot selection change"""
        try:
            selection = self.bot_combo.get()
            if not selection or "(create first bot)" in selection:
                return
            
            # Extract bot ID from display string "✅ Name (bot_id)"
            if "(" in selection and selection.endswith(")"):
                bot_id = selection.split("(")[-1].rstrip(")")
                bot_data = self.registry.get_bot(bot_id)
                license_key = bot_data.get('license_key', '')
                self.license_key_var.set(license_key)
                self._update_license_status()
                self._update_bot_info()
                
        except Exception as e:
            self.logger.exception("Error handling bot selection")
    
    def _add_bot(self):
        """Add new bot dialog"""
        try:
            bot_id = simpledialog.askstring("Add Bot", "Enter Bot ID (unique identifier):", parent=self.root)
            if not bot_id:
                return
            
            bot_id = bot_id.strip()
            if bot_id in self.registry.list_bots():
                messagebox.showerror("Error", f"Bot '{bot_id}' already exists!")
                return
                
            bot_name = simpledialog.askstring("Add Bot", f"Enter display name for '{bot_id}':", parent=self.root, initialvalue=bot_id)
            if not bot_name:
                bot_name = bot_id
            
            if self.registry.add_bot(bot_id, bot_name.strip()):
                self._refresh_bot_list()
                self.logger.info(f"Bot added: {bot_id} ({bot_name})")
                messagebox.showinfo("Success", f"Bot '{bot_id}' added successfully!")
            else:
                messagebox.showerror("Error", "Failed to add bot")
                
        except Exception as e:
            self.logger.exception("Error adding bot")
            messagebox.showerror("Add Bot Error", f"Failed to add bot: {e}")
    
    def _remove_bot(self):
        """Remove selected bot"""
        try:
            active_bot = self.registry.get_active_bot()
            if not active_bot:
                messagebox.showwarning("Warning", "No bot selected")
                return
                
            if messagebox.askyesno("Confirm", f"Remove bot '{active_bot}'?\n\nThis cannot be undone."):
                if self.registry.remove_bot(active_bot):
                    self._refresh_bot_list()
                    self.logger.info(f"Bot removed: {active_bot}")
                    messagebox.showinfo("Success", f"Bot '{active_bot}' removed")
                else:
                    messagebox.showerror("Error", "Failed to remove bot")
                    
        except Exception as e:
            self.logger.exception("Error removing bot")
            messagebox.showerror("Remove Bot Error", f"Failed to remove bot: {e}")
    
    def _set_active_bot(self):
        """Set selected bot as active"""
        try:
            selection = self.bot_combo.get()
            if not selection or "(create first bot)" in selection:
                return
            
            # Extract bot ID from display string
            if "(" in selection and selection.endswith(")"):
                bot_id = selection.split("(")[-1].rstrip(")")
                if self.registry.set_active_bot(bot_id):
                    self._refresh_bot_list()
                    self._update_bot_info()
                    self.logger.info(f"Active bot changed to: {bot_id}")
                    messagebox.showinfo("Success", f"Active bot set to: {bot_id}")
                    
                    # Suggest restart if bot is running
                    if self.is_running:
                        if messagebox.askyesno("Restart Bot", "Bot is currently running.\n\nRestart with new active bot?"):
                            self._restart_bot()
                else:
                    messagebox.showerror("Error", "Failed to set active bot")
                    
        except Exception as e:
            self.logger.exception("Error setting active bot")
            messagebox.showerror("Set Active Error", f"Failed to set active bot: {e}")
    
    def _validate_license(self):
        """Validate entered license key"""
        try:
            key = self.license_key_var.get().strip()
            if not key:
                messagebox.showwarning("Warning", "Enter license key first")
                return
                
            token = self.config.get_bot_token()
            if not token:
                messagebox.showerror("Error", "No bot token configured! Set token first in Configuration.")
                return
                
            status = self.licenser.validate_key(key, bot_token=token, hwid=self.licenser.get_hwid())
            
            if status.get('valid'):
                messagebox.showinfo("License Valid", f"✅ License is valid!\n\nExpires: 20{status.get('expires', 'XX')}")
            else:
                messagebox.showerror("License Invalid", f"❌ License is invalid.\n\nReason: {status.get('reason', 'Unknown')}")
                
            self._update_license_status()
            
        except Exception as e:
            self.logger.exception("Error validating license")
            messagebox.showerror("Validation Error", f"Failed to validate license: {e}")
    
    def _activate_license(self):
        """Activate license for current bot"""
        try:
            key = self.license_key_var.get().strip()
            if not key:
                messagebox.showwarning("Warning", "Enter license key first")
                return
                
            active_bot = self.registry.get_active_bot()
            if not active_bot:
                messagebox.showerror("Error", "No active bot selected")
                return
                
            result = self.registry.set_license(active_bot, key)
            
            if result.get('ok'):
                messagebox.showinfo("Success", f"✅ License activated for bot: {active_bot}")
                self.logger.info(f"License activated for bot: {active_bot}")
            else:
                messagebox.showerror("Activation Failed", f"❌ Failed to activate license.\n\nStatus: {result.get('status', {})}")
                
            self._refresh_bot_list()
            self._update_license_status()
            self._update_bot_info()
            
        except Exception as e:
            self.logger.exception("Error activating license")
            messagebox.showerror("Activation Error", f"Failed to activate license: {e}")
    
    def _generate_license(self):
        """Open license generator dialog"""
        try:
            dialog = LicenseDialog(self.root)
            self.root.wait_window(dialog.dialog)
            
            if dialog.result:
                self.license_key_var.set(dialog.result)
                self._update_license_status()
                
        except Exception as e:
            self.logger.exception("Error generating license")
            messagebox.showerror("Generation Error", f"Failed to generate license: {e}")
    
    def _show_hwid(self):
        """Show hardware ID"""
        try:
            hwid = self.licenser.get_hwid()
            messagebox.showinfo("Hardware ID", f"Your Hardware ID: {hwid}\n\nThis ID is used for hardware-locked licenses.")
            
        except Exception as e:
            self.logger.exception("Error getting HWID")
            messagebox.showerror("HWID Error", f"Failed to get hardware ID: {e}")
    
    def _show_license_info(self):
        """Show detailed license information"""
        try:
            key = self.license_key_var.get().strip()
            if not key:
                messagebox.showwarning("Warning", "Enter license key first")
                return
                
            try:
                parsed = self.licenser.parse_key(key)
                info = f"""License Key Information:

Token Hash: {parsed['token_hash']}
Expiry Date: 20{parsed['expiry']} (YYMMDD format)
Hardware ID: {parsed['hw']}
Checksum: {parsed['csum']}

Key Format: TPMB-{parsed['token_hash'][:4]}-{parsed['token_hash'][4:8]}-{parsed['expiry'][:4]}-{parsed['expiry'][4:8]}-{parsed['hw'][:4]}-{parsed['hw'][4:8]}-{parsed['csum']}"""
                
                messagebox.showinfo("License Information", info)
                
            except Exception as parse_error:
                messagebox.showerror("Parse Error", f"Invalid license key format:\n{parse_error}")
                
        except Exception as e:
            self.logger.exception("Error showing license info")
            messagebox.showerror("License Info Error", f"Failed to show license info: {e}")
    
    def _update_license_status(self):
        """Update license status display"""
        try:
            active_bot = self.registry.get_active_bot()
            if not active_bot:
                self.license_status_var.set("No active bot selected")
                self.license_var.set("❌ No Bot")
                return
                
            bot_data = self.registry.get_bot(active_bot)
            license_key = bot_data.get('license_key', '')
            
            if not license_key:
                self.license_status_var.set("No license key configured")
                self.license_var.set("❌ No License")
                return
                
            token = self.config.get_bot_token()
            if not token:
                self.license_status_var.set("No bot token configured")
                self.license_var.set("❌ No Token")
                return
                
            try:
                status = self.licenser.validate_key(license_key, bot_token=token, hwid=self.licenser.get_hwid())
                
                if status.get('valid'):
                    self.license_status_var.set(f"✅ License active (expires: 20{status.get('expires', 'XX')})")
                    self.license_var.set("✅ Active")
                    self.license_label.config(foreground="green")
                else:
                    reason = status.get('reason', 'unknown')
                    self.license_status_var.set(f"❌ License invalid: {reason}")
                    if 'expired' in reason:
                        self.license_var.set("⚠️ Expired")
                        self.license_label.config(foreground="orange")
                    else:
                        self.license_var.set("❌ Invalid")
                        self.license_label.config(foreground="red")
                        
            except Exception as e:
                self.license_status_var.set(f"Error validating license: {str(e)[:50]}")
                self.license_var.set("❌ Error")
                self.license_label.config(foreground="red")
                
        except Exception as e:
            self.logger.exception("Error updating license status")
    
    # ... (rest of the methods remain the same as before)
    def _create_config_tab(self, parent):
        try:
            parent.columnconfigure(1, weight=1)
            
            # Token section
            ttk.Label(parent, text="Bot Token:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.token_var = tk.StringVar()
            ttk.Entry(parent, textvariable=self.token_var, show="*", width=50).grid(row=0, column=1, sticky=tk.EW, padx=10)
            token_frame = ttk.Frame(parent)
            token_frame.grid(row=0, column=2)
            ttk.Button(token_frame, text="Save Token", command=self._save_token).pack(side=tk.LEFT)
            ttk.Button(token_frame, text="Test Connection", command=self._test_connection).pack(side=tk.LEFT, padx=(5,0))
            
            # Templates section
            templates_frame = ttk.LabelFrame(parent, text="Message Templates", padding=8)
            templates_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, padx=10, pady=(10,0))
            templates_frame.columnconfigure(1, weight=1)
            
            ttk.Label(templates_frame, text="Active Template:").grid(row=0, column=0, sticky=tk.W)
            self.template_var = tk.StringVar(value=self.config.get_active_template_key())
            self.template_combo = ttk.Combobox(templates_frame, textvariable=self.template_var, state="readonly")
            self._reload_templates_into_combo()
            self.template_combo.grid(row=0, column=1, sticky=tk.EW, padx=(8,0))
            ttk.Button(templates_frame, text="Set Active", command=self._set_active_template).grid(row=0, column=2, padx=(8,0))
            ttk.Button(templates_frame, text="New", command=self._new_template).grid(row=0, column=3, padx=(4,0))
            ttk.Button(templates_frame, text="Delete", command=self._delete_template).grid(row=0, column=4, padx=(4,0))
            
            # Message editor
            ttk.Label(parent, text="Message (active template):").grid(row=2, column=0, sticky=(tk.W,tk.N), pady=(10,2))
            self.msg_text = scrolledtext.ScrolledText(parent, width=60, height=6)
            self.msg_text.grid(row=2, column=1, columnspan=2, sticky=tk.EW, padx=10, pady=(10,5))
            self.msg_text.insert('1.0', self.config.get_message_text())
            
            ttk.Button(parent, text="Save Message", command=self._save_message).grid(row=3, column=1, sticky=tk.W, padx=10)
            
            # Proxy section
            self._create_proxy_section(parent)
            
            # Diagnostics section
            diag_frame = ttk.LabelFrame(parent, text="Diagnostics", padding=8)
            diag_frame.grid(row=5, column=0, columnspan=3, sticky=tk.EW, padx=10, pady=(10,0))
            ttk.Button(diag_frame, text="Run Diagnostics", command=self._run_diagnostics).pack(side=tk.LEFT)
            ttk.Button(diag_frame, text="View Logs Folder", command=self._open_logs_folder).pack(side=tk.LEFT, padx=(10,0))
            
        except Exception as e:
            self.logger.exception("Error creating config tab")
            messagebox.showerror("Config Tab Error", f"Failed to create configuration tab: {e}")
    
    def _create_proxy_section(self, parent):
        try:
            proxy_frame = ttk.LabelFrame(parent, text="SOCKS5 Proxy (Optional)", padding=10)
            proxy_frame.grid(row=4, column=0, columnspan=3, sticky=tk.EW, padx=10, pady=(20,0))
            proxy_frame.columnconfigure(1, weight=1)
            
            self.proxy_enabled_var = tk.BooleanVar()
            self.proxy_host_var = tk.StringVar()
            self.proxy_port_var = tk.StringVar()
            self.proxy_username_var = tk.StringVar()
            self.proxy_password_var = tk.StringVar()
            
            self._load_proxy_config()
            
            ttk.Checkbutton(proxy_frame, text="Enable SOCKS5 Proxy", variable=self.proxy_enabled_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
            
            ttk.Label(proxy_frame, text="Host:").grid(row=1, column=0, sticky=tk.W, pady=2)
            ttk.Entry(proxy_frame, textvariable=self.proxy_host_var, width=20).grid(row=1, column=1, sticky=tk.W, padx=(10,0))
            
            ttk.Label(proxy_frame, text="Port:").grid(row=1, column=2, sticky=tk.W, padx=(20,5))
            ttk.Entry(proxy_frame, textvariable=self.proxy_port_var, width=8).grid(row=1, column=3, sticky=tk.W)
            
            ttk.Label(proxy_frame, text="Username:").grid(row=2, column=0, sticky=tk.W, pady=2)
            ttk.Entry(proxy_frame, textvariable=self.proxy_username_var, width=20).grid(row=2, column=1, sticky=tk.W, padx=(10,0))
            
            ttk.Label(proxy_frame, text="Password:").grid(row=2, column=2, sticky=tk.W, padx=(20,5))
            ttk.Entry(proxy_frame, textvariable=self.proxy_password_var, show="*", width=20).grid(row=2, column=3, sticky=tk.W)
            
            button_frame = ttk.Frame(proxy_frame)
            button_frame.grid(row=3, column=0, columnspan=4, pady=(10,0))
            ttk.Button(button_frame, text="Save Proxy Config", command=self._save_proxy_config).pack(side=tk.LEFT)
            ttk.Button(button_frame, text="Test Connection", command=self._test_connection).pack(side=tk.LEFT, padx=(10,0))
            
        except Exception as e:
            self.logger.exception("Error creating proxy section")
    
    def _create_logs_tab(self, parent):
        try:
            parent.columnconfigure(0, weight=1)
            parent.rowconfigure(1, weight=1)
            
            # Controls
            ctrl_frame = ttk.Frame(parent)
            ctrl_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0,10))
            ttk.Button(ctrl_frame, text="Refresh", command=self._refresh_logs).grid(row=0, column=0)
            ttk.Button(ctrl_frame, text="Clear", command=self._clear_logs).grid(row=0, column=1, padx=(10,0))
            ttk.Button(ctrl_frame, text="Open Logs Folder", command=self._open_logs_folder).grid(row=0, column=2, padx=(10,0))
            
            # Logs display
            self.logs_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, font=('Consolas', 9))
            self.logs_text.grid(row=1, column=0, sticky=(tk.W,tk.E,tk.N,tk.S))
            self._refresh_logs()
            
        except Exception as e:
            self.logger.exception("Error creating logs tab")
    
    def _create_groups_tab(self, parent):
        try:
            parent.columnconfigure(0, weight=1)
            parent.rowconfigure(3, weight=1)
            
            # Single add controls
            ctrl_frame = ttk.Frame(parent)
            ctrl_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0,10))
            
            ttk.Label(ctrl_frame, text="Group ID:").grid(row=0, column=0)
            self.group_var = tk.StringVar()
            ttk.Entry(ctrl_frame, textvariable=self.group_var, width=20).grid(row=0, column=1, padx=(5,0))
            
            ttk.Label(ctrl_frame, text="Name:").grid(row=0, column=2, padx=(10,5))
            self.group_name_var = tk.StringVar()
            ttk.Entry(ctrl_frame, textvariable=self.group_name_var, width=20).grid(row=0, column=3, padx=(5,0))
            
            ttk.Button(ctrl_frame, text="Add", command=self._add_group).grid(row=0, column=4, padx=(10,0))
            
            # Bulk paste area
            bulk_frame = ttk.LabelFrame(parent, text="Bulk add groups (one per line, supports 'ID;Name' format)")
            bulk_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=0, pady=(0,10))
            self.bulk_groups_text = scrolledtext.ScrolledText(bulk_frame, height=5, width=60)
            self.bulk_groups_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
            
            bulk_buttons = ttk.Frame(parent)
            bulk_buttons.grid(row=2, column=0, sticky=tk.W, pady=(0,10))
            ttk.Button(bulk_buttons, text="Add Bulk", command=self._add_bulk_groups).pack(side=tk.LEFT)
            ttk.Button(bulk_buttons, text="Clear Bulk", command=lambda: self.bulk_groups_text.delete('1.0', tk.END)).pack(side=tk.LEFT, padx=6)
            ttk.Button(bulk_buttons, text="Deduplicate", command=self._deduplicate_groups).pack(side=tk.LEFT, padx=6)
            
            # Groups list with management
            list_frame = ttk.Frame(parent)
            list_frame.grid(row=3, column=0, sticky=(tk.W,tk.E,tk.N,tk.S))
            list_frame.columnconfigure(0, weight=1)
            list_frame.rowconfigure(0, weight=1)
            
            # Groups list
            self.groups_list = tk.Listbox(list_frame)
            self.groups_list.grid(row=0, column=0, sticky=(tk.W,tk.E,tk.N,tk.S), padx=(0,10))
            
            # Management buttons
            mgmt_frame = ttk.Frame(list_frame)
            mgmt_frame.grid(row=0, column=1, sticky=(tk.N,tk.S))
            ttk.Button(mgmt_frame, text="Edit Selected", command=self._edit_selected_group).pack(pady=(0,5))
            ttk.Button(mgmt_frame, text="Remove Selected", command=self._remove_group).pack(pady=5)
            
            self._refresh_groups()
            
        except Exception as e:
            self.logger.exception("Error creating groups tab")
    
    # Template methods
    def _reload_templates_into_combo(self):
        try:
            keys = self.config.list_templates()
            self.template_combo["values"] = keys
            current_key = self.config.get_active_template_key()
            if current_key not in keys and keys:
                self.template_var.set(keys[0])
            else:
                self.template_var.set(current_key)
        except Exception as e:
            self.logger.exception("Error reloading templates")
    
    def _set_active_template(self):
        try:
            key = self.template_var.get().strip()
            self.config.set_active_template_key(key)
            self.msg_text.delete('1.0', tk.END)
            self.msg_text.insert('1.0', self.config.get_message_text())
            messagebox.showinfo("Templates", f"Active template set to: {key}")
            self.logger.info(f"Active template changed to: {key}")
        except Exception as e:
            self.logger.exception("Error setting active template")
            messagebox.showerror("Template Error", f"Failed to set active template: {e}")
    
    def _new_template(self):
        try:
            key = simpledialog.askstring("New Template", "Template key (a-z,0-9,_):", parent=self.root)
            if not key:
                return
            key = key.strip()
            if key in self.config.list_templates():
                messagebox.showerror("Templates", "Template key already exists")
                return
            self.config.set_template(key, "New template text {timestamp}")
            self.config.set_active_template_key(key)
            self._reload_templates_into_combo()
            self.msg_text.delete('1.0', tk.END)
            self.msg_text.insert('1.0', self.config.get_message_text())
            self.logger.info(f"New template created: {key}")
        except Exception as e:
            self.logger.exception("Error creating new template")
            messagebox.showerror("Template Error", f"Failed to create template: {e}")
    
    def _delete_template(self):
        try:
            key = self.template_var.get().strip()
            active_key = self.config.get_active_template_key()
            if key == active_key:
                messagebox.showerror("Templates", "Cannot delete the active template")
                return
            if messagebox.askyesno("Templates", f"Delete template '{key}'?"):
                if self.config.remove_template(key):
                    self._reload_templates_into_combo()
                    self.msg_text.delete('1.0', tk.END)
                    self.msg_text.insert('1.0', self.config.get_message_text())
                    self.logger.info(f"Template deleted: {key}")
        except Exception as e:
            self.logger.exception("Error deleting template")
            messagebox.showerror("Template Error", f"Failed to delete template: {e}")
    
    # Proxy methods
    def _load_proxy_config(self):
        try:
            proxy_config = self.config.get_proxy_config()
            self.proxy_enabled_var.set(proxy_config.get("enabled", False))
            self.proxy_host_var.set(proxy_config.get("host", "127.0.0.1"))
            self.proxy_port_var.set(str(proxy_config.get("port", 1080)))
            self.proxy_username_var.set(proxy_config.get("username", ""))
            # Don't load password for security
        except Exception as e:
            self.logger.exception("Error loading proxy config")
    
    def _save_proxy_config(self):
        try:
            port = int(self.proxy_port_var.get())
            if port < 1 or port > 65535:
                raise ValueError("Port must be 1-65535")
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
            return
        
        try:
            self.config.set_proxy_config(
                enabled=self.proxy_enabled_var.get(),
                host=self.proxy_host_var.get(),
                port=port,
                username=self.proxy_username_var.get(),
                password=self.proxy_password_var.get()
            )
            self.proxy_password_var.set("")  # Clear password field
            messagebox.showinfo("Success", "Proxy configuration saved!")
            self.logger.info("Proxy configuration updated")
            self._suggest_restart("Proxy configuration changed")
        except Exception as e:
            self.logger.exception("Error saving proxy config")
            messagebox.showerror("Proxy Error", f"Failed to save proxy config: {e}")
    
    def _test_connection(self):
        """Test connection to Telegram API (with proxy if enabled)"""
        try:
            self.root.config(cursor="watch")
            self.root.update()
            
            from bot.security import SecurityManager
            security = SecurityManager()
            
            # Test basic connectivity
            if security.verify_telegram_api():
                proxy_status = "Using proxy" if self.config.get_proxy_config().get("enabled") else "Direct connection"
                messagebox.showinfo("Connection Test", f"✅ Connection to Telegram API successful!\n\n{proxy_status}")
                self.logger.info(f"Connection test successful ({proxy_status})")
            else:
                messagebox.showerror("Connection Test", "❌ Failed to connect to Telegram API")
                self.logger.error("Connection test failed")
                
        except Exception as e:
            self.logger.exception("Connection test error")
            messagebox.showerror("Connection Test", f"❌ Connection test failed:\n{e}")
        finally:
            self.root.config(cursor="")
    
    # Bot control methods
    def _suggest_restart(self, reason: str):
        """Suggest restart after configuration changes"""
        if self.is_running:
            if messagebox.askyesno("Restart Recommended", f"{reason}.\n\nRestart bot to apply changes?"):
                self._restart_bot()
    
    def _start_bot(self):
        try:
            if self.is_running:
                messagebox.showinfo("Info", "Bot is already running")
                return
            
            if not self.config.get_bot_token():
                messagebox.showerror("Error", "Configure bot token first!")
                return
            
            from bot.core import TelegramBot
            self.bot = TelegramBot()
            self.bot_thread = threading.Thread(target=self._run_bot_async, daemon=True)
            self.bot_thread.start()
            
            self.is_running = True
            self.start_btn.config(state=tk.DISABLED)
            self.restart_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
            self.status_var.set("Starting...")
            messagebox.showinfo("Started", "Bot started in background. Check logs for details.")
            self.logger.info("Bot start initiated")
            
        except Exception as e:
            self.logger.exception("Error starting bot")
            messagebox.showerror("Error", f"Failed to start bot: {e}")
    
    def _restart_bot(self):
        """Graceful restart without closing GUI"""
        try:
            if not self.is_running:
                messagebox.showinfo("Info", "Bot is not running. Use Start instead.")
                return
            
            self.status_var.set("Restarting...")
            self.root.update()
            
            # Restart messaging in bot instance
            if self.bot:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.bot.restart_messaging())
                loop.close()
            
            messagebox.showinfo("Restarted", "Bot restarted successfully!")
            self.logger.info("Bot restarted successfully")
            
        except Exception as e:
            self.logger.exception("Error restarting bot")
            messagebox.showerror("Error", f"Failed to restart bot: {e}")
            self._bot_stopped()
    
    def _run_bot_async(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.bot.run())
        except Exception as e:
            self.logger.exception("Bot runtime error")
            self.root.after(0, lambda: self._bot_error(str(e)))
        finally:
            self.root.after(0, self._bot_stopped)
    
    def _bot_error(self, error):
        messagebox.showerror("Bot Error", f"Bot encountered error: {error}")
        self._bot_stopped()
    
    def _bot_stopped(self):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.restart_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Stopped")
        self.logger.info("Bot stopped")
    
    def _stop_bot(self):
        try:
            if not self.is_running:
                return
            if self.bot:
                asyncio.run_coroutine_threadsafe(self.bot.shutdown(), asyncio.get_event_loop())
            self._bot_stopped()
            self.logger.info("Bot stop initiated")
        except Exception as e:
            self.logger.exception("Error stopping bot")
            self._bot_stopped()
    
    # Configuration methods
    def _save_token(self):
        try:
            token = self.token_var.get().strip()
            if not token:
                messagebox.showerror("Error", "Enter bot token!")
                return
            self.config.set_bot_token(token)
            self.token_var.set("")
            messagebox.showinfo("Success", "Token saved and encrypted!")
            self.logger.info("Bot token updated")
            # Update license status after token change
            self._update_license_status()
            # Token change requires manual restart
            if self.is_running:
                messagebox.showwarning("Restart Required", "Token changed. Please STOP and START the bot manually.")
        except Exception as e:
            self.logger.exception("Error saving token")
            messagebox.showerror("Token Error", f"Failed to save token: {e}")
    
    def _save_message(self):
        try:
            msg = self.msg_text.get('1.0', tk.END).strip()
            if not msg:
                messagebox.showerror("Error", "Message cannot be empty!")
                return
            self.config.set_message_text(msg)
            messagebox.showinfo("Success", "Message saved!")
            self.logger.info("Message template updated")
            self._suggest_restart("Message changed")
        except Exception as e:
            self.logger.exception("Error saving message")
            messagebox.showerror("Message Error", f"Failed to save message: {e}")
    
    def _update_interval(self, event=None):
        try:
            interval = int(self.interval_var.get())
            if interval < 1:
                raise ValueError("Interval must be > 0")
            self.config.set_interval_minutes(interval)
            messagebox.showinfo("Success", f"Global interval set to {interval} minutes")
            self.logger.info(f"Global interval updated to {interval} minutes")
            self._suggest_restart("Global interval changed")
        except ValueError:
            messagebox.showerror("Error", "Enter valid number of minutes!")
            self.interval_var.set(str(self.config.get_interval_minutes()))
        except Exception as e:
            self.logger.exception("Error updating interval")
            messagebox.showerror("Interval Error", f"Failed to update interval: {e}")
    
    # Group management methods
    def _normalize_group_id(self, raw: str) -> int:
        val = raw.strip()
        if not val:
            raise ValueError("empty")
        # auto-prefix -100 if needed
        if val.startswith("-100"):
            return int(val)
        if val.startswith("-"):
            return int("-100" + val.lstrip("-"))
        # plain digits -> add -100 prefix
        return int("-100" + val)
    
    def _add_group(self):
        try:
            gid = self._normalize_group_id(self.group_var.get())
            name = self.group_name_var.get().strip() or None
            
            if self.config.add_group(gid, name):
                self.group_var.set("")
                self.group_name_var.set("")
                self._refresh_groups()
                self._update_status()
                self.logger.info(f"Group added: {gid} ({name})")
                self._suggest_restart("Group added")
            else:
                messagebox.showwarning("Duplicate", f"Group {gid} already exists!")
        except Exception as e:
            self.logger.exception("Error adding group")
            messagebox.showerror("Error", f"Invalid Group ID: {e}")
    
    def _add_bulk_groups(self):
        try:
            text = self.bulk_groups_text.get('1.0', tk.END)
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            added, skipped = 0, 0
            
            for ln in lines:
                try:
                    # Support "ID;Name" format
                    if ';' in ln:
                        id_part, name_part = ln.split(';', 1)
                        gid = self._normalize_group_id(id_part)
                        name = name_part.strip() or None
                    else:
                        gid = self._normalize_group_id(ln)
                        name = None
                    
                    if self.config.add_group(gid, name):
                        added += 1
                    else:
                        skipped += 1  # Duplicate
                except Exception:
                    skipped += 1
            
            self._refresh_groups()
            self._update_status()
            messagebox.showinfo("Bulk Add", f"Added: {added}\nSkipped (duplicates/invalid): {skipped}")
            self.logger.info(f"Bulk add completed: {added} added, {skipped} skipped")
            if added > 0:
                self._suggest_restart("Groups added")
        except Exception as e:
            self.logger.exception("Error in bulk add")
            messagebox.showerror("Bulk Add Error", f"Failed to add groups: {e}")
    
    def _edit_selected_group(self):
        try:
            sel = self.groups_list.curselection()
            if not sel:
                messagebox.showwarning("Selection", "Please select a group to edit")
                return
            
            # Parse selected item to get group ID
            item = self.groups_list.get(sel[0])
            try:
                gid = int(item.split()[0])
            except (ValueError, IndexError):
                messagebox.showerror("Error", "Cannot parse group ID")
                return
            
            # Get current group data
            group = self.config.get_group_by_id(gid)
            if not group:
                messagebox.showerror("Error", "Group not found")
                return
            
            # Open edit dialog
            dialog = GroupEditDialog(
                self.root, 
                group_id=gid, 
                group_name=group.get("name", ""), 
                group_interval=group.get("interval")
            )
            self.root.wait_window(dialog.dialog)
            
            if dialog.result:
                name, interval = dialog.result
                if self.config.update_group(gid, name=name, interval=interval):
                    self._refresh_groups()
                    messagebox.showinfo("Success", "Group updated!")
                    self.logger.info(f"Group updated: {gid} -> name='{name}', interval={interval}")
                    self._suggest_restart("Group updated")
        except Exception as e:
            self.logger.exception("Error editing group")
            messagebox.showerror("Edit Error", f"Failed to edit group: {e}")
    
    def _deduplicate_groups(self):
        try:
            removed = self.config.deduplicate_groups()
            if removed > 0:
                self._refresh_groups()
                self._update_status()
                messagebox.showinfo("Deduplicate", f"Removed {removed} duplicate groups")
                self.logger.info(f"Deduplication completed: {removed} duplicates removed")
                self._suggest_restart("Groups deduplicated")
            else:
                messagebox.showinfo("Deduplicate", "No duplicates found")
        except Exception as e:
            self.logger.exception("Error deduplicating groups")
            messagebox.showerror("Deduplicate Error", f"Failed to deduplicate: {e}")
    
    def _remove_group(self):
        try:
            sel = self.groups_list.curselection()
            if not sel:
                return
            item = self.groups_list.get(sel[0])
            try:
                gid = int(item.split()[0])
            except (ValueError, IndexError):
                return
            
            if self.config.remove_group(gid):
                self._refresh_groups()
                self._update_status()
                self.logger.info(f"Group removed: {gid}")
                self._suggest_restart("Group removed")
        except Exception as e:
            self.logger.exception("Error removing group")
    
    def _refresh_groups(self):
        try:
            self.groups_list.delete(0, tk.END)
            groups = self.config.get_groups_objects()
            global_interval = self.config.get_interval_minutes()
            
            for group in groups:
                gid = group["id"]
                name = group.get("name")
                interval = group.get("interval")
                
                display_name = f" — {name}" if name else " — (no name)"
                interval_str = f" (every {interval} min)" if interval else f" (global: {global_interval} min)"
                
                display = f"{gid}{display_name}{interval_str}"
                self.groups_list.insert(tk.END, display)
        except Exception as e:
            self.logger.exception("Error refreshing groups")
    
    # Logging methods
    def _refresh_logs(self):
        try:
            log_path = os.path.join("logs", "bot.log")
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    recent = lines[-200:] if len(lines) > 200 else lines
                    content = ''.join(recent)
            else:
                content = "No logs yet. Start the bot to see logs."
            
            self.logs_text.delete('1.0', tk.END)
            self.logs_text.insert('1.0', content)
            self.logs_text.see(tk.END)
        except Exception as e:
            self.logger.exception("Error refreshing logs")
            self.logs_text.delete('1.0', tk.END)
            self.logs_text.insert('1.0', f"Error loading logs: {e}")
    
    def _clear_logs(self):
        try:
            if messagebox.askyesno("Confirm", "Clear all logs?"):
                for log_file in ["bot.log", "error.log", "error-startup.log"]:
                    log_path = os.path.join("logs", log_file)
                    if os.path.exists(log_path):
                        open(log_path, 'w').close()
                self._refresh_logs()
                messagebox.showinfo("Success", "Logs cleared!")
                self.logger.info("Logs cleared")
        except Exception as e:
            self.logger.exception("Error clearing logs")
            messagebox.showerror("Error", f"Failed to clear logs: {e}")
    
    def _open_logs_folder(self):
        try:
            logs_dir = os.path.join(current_dir, "logs")
            if os.path.exists(logs_dir):
                os.startfile(logs_dir)  # Windows
            else:
                messagebox.showinfo("Info", f"Logs directory not found: {logs_dir}")
        except Exception as e:
            self.logger.exception("Error opening logs folder")
            messagebox.showerror("Error", f"Failed to open logs folder: {e}")
    
    # Diagnostics
    def _run_diagnostics(self):
        try:
            from utils.logger import create_diagnostics_report
            report_path = create_diagnostics_report(self.config)
            
            # Show summary in dialog
            summary = f"""Diagnostics completed!

Report saved to: {report_path}

Quick summary:
• Python: {sys.version.split()[0]}
• Groups: {len(self.config.get_groups())}
• Active Template: {self.config.get_active_template_key()}
• Proxy: {'Enabled' if self.config.get_proxy_config().get('enabled') else 'Disabled'}
• Active Bot: {self.registry.get_active_bot() or 'None'}
• License: {self.license_var.get()}

View full report in logs folder."""
            
            messagebox.showinfo("Diagnostics", summary)
            self.logger.info("Diagnostics report generated")
            
        except Exception as e:
            self.logger.exception("Error running diagnostics")
            messagebox.showerror("Diagnostics Error", f"Failed to run diagnostics: {e}")
    
    # Update system
    def _safe_update_from_github(self):
        """Updater with comprehensive SSL handling and error recovery"""
        try:
            if not messagebox.askyesno("Update", "Download and apply latest update from GitHub?\nConfig and logs will be preserved."):
                return
            
            zip_url = "https://codeload.github.com/pizdziaty-garfild/tpmb2/zip/refs/heads/main"
            headers = {"User-Agent": "TPMB2-Updater"}
            
            # First attempt: verified SSL using certifi
            try:
                import certifi
                cafile = certifi.where()
                ctx = ssl.create_default_context(cafile=cafile)
                req = Request(zip_url, headers=headers)
                self.root.config(cursor="watch")
                self.root.update()
                with urlopen(req, timeout=30, context=ctx) as resp:
                    data = resp.read()
                self.logger.info("Update downloaded with SSL verification")
            except Exception as e_verified:
                self.root.config(cursor="")
                self.logger.warning(f"SSL verification failed: {e_verified}")
                if not messagebox.askyesno("Update (SSL)", f"Verified download failed:\n{str(e_verified)[:200]}\n\nRetry WITHOUT certificate verification?\n(Not recommended for security)"):
                    return
                # Fallback: unverified context
                unverified = ssl.create_default_context()
                unverified.check_hostname = False
                unverified.verify_mode = ssl.CERT_NONE
                req = Request(zip_url, headers=headers)
                self.root.config(cursor="watch")
                self.root.update()
                with urlopen(req, timeout=30, context=unverified) as resp:
                    data = resp.read()
                self.logger.info("Update downloaded without SSL verification")
            
            # Extract and copy
            zf = zipfile.ZipFile(io.BytesIO(data))
            tmpdir = tempfile.mkdtemp(prefix="tpmb2_update_")
            zf.extractall(tmpdir)
            top = next((name for name in zf.namelist() if name.endswith('/')), None)
            base = os.path.join(tmpdir, top) if top else tmpdir
            
            whitelist = [
                "main.py", "requirements.txt", ".gitignore", "README.md",
                os.path.join("bot"), os.path.join("utils")
            ]
            preserved = ["config", "logs"]
            
            copied = 0
            for root_dir, dirs, files in os.walk(base):
                rel_root = os.path.relpath(root_dir, base)
                if rel_root == ".":
                    rel_root = ""
                if any(rel_root.startswith(p) for p in preserved if rel_root != ""):
                    continue
                if rel_root != "" and not any(rel_root.split(os.sep)[0] == os.path.normpath(w).split(os.sep)[0] for w in whitelist):
                    continue
                target_root = os.path.join(current_dir, rel_root) if rel_root else current_dir
                os.makedirs(target_root, exist_ok=True)
                for f in files:
                    src = os.path.join(root_dir, f)
                    dst = os.path.join(target_root, f)
                    if any(dst.startswith(os.path.join(current_dir, p)) for p in preserved):
                        continue
                    with open(src, 'rb') as rf, open(dst, 'wb') as wf:
                        wf.write(rf.read())
                        copied += 1
            
            self.root.config(cursor="")
            messagebox.showinfo("Update", f"Update applied successfully!\n\nFiles updated: {copied}\nPreserved: config/, logs/\n\nPlease restart the application.")
            self.logger.info(f"Update completed successfully: {copied} files updated")
            
        except Exception as e:
            self.root.config(cursor="")
            self.logger.exception("Update failed")
            error_msg = f"Cannot update: {str(e)[:300]}"
            messagebox.showerror("Update Failed", f"{error_msg}\n\nCheck logs for details.")
    
    # Status and lifecycle
    def _update_status(self):
        try:
            groups_count = len(self.config.get_groups())
            self.groups_var.set(str(groups_count))
            
            if self.is_running:
                self.status_var.set("Running")
                self.status_label.config(foreground="green")
            else:
                self.status_var.set("Stopped")
                self.status_label.config(foreground="red")
            
            # Update license status
            self._update_license_status()
            
        except Exception as e:
            self.logger.exception("Error updating status")
    
    def _periodic_update(self):
        try:
            self._update_status()
            self.root.after(5000, self._periodic_update)
        except Exception as e:
            self.logger.exception("Error in periodic update")
            # Continue periodic updates even if one fails
            self.root.after(10000, self._periodic_update)
    
    def _on_close(self):
        try:
            if self.is_running:
                if messagebox.askyesno("Confirm", "Bot is running. Stop and exit?"):
                    self._stop_bot()
                    self.root.after(1000, self.root.destroy)
            else:
                self.root.destroy()
        except Exception as e:
            self.logger.exception("Error during shutdown")
            self.root.destroy()
    
    def run(self):
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            self.root.mainloop()
        except Exception as e:
            self.logger.exception("Error in main loop")
            messagebox.showerror("Critical Error", f"Application error: {e}")

if __name__ == "__main__":
    try:
        # Ensure logs directory exists before any logging
        ensure_logs_directory()
        
        # Create and run application
        app = TPMB2GUI()
        app.run()
        
    except Exception as e:
        # Ultimate fallback error handling
        tb_str = traceback.format_exc()
        error_msg = f"Critical startup failure: {str(e)}"
        
        # Log to file
        try:
            log_startup_error(error_msg, tb_str)
        except:
            pass  # If logging fails, continue to show dialog
        
        # Show error dialog with copy button
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()  # Hide main window
            
            error_text = f"""{error_msg}

Full traceback:
{tb_str}

This error has been logged to logs/error-startup.log"""
            
            # Create custom dialog with copy functionality
            dialog = tk.Toplevel(root)
            dialog.title("TPMB2 Critical Error")
            dialog.geometry("600x400")
            
            tk.Label(dialog, text="TPMB2 failed to start. Copy details below:", font=('Arial', 10, 'bold')).pack(pady=5)
            
            text_widget = tk.Text(dialog, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            text_widget.insert('1.0', error_text)
            text_widget.config(state=tk.DISABLED)
            
            def copy_to_clipboard():
                dialog.clipboard_clear()
                dialog.clipboard_append(error_text)
                messagebox.showinfo("Copied", "Error details copied to clipboard")
            
            button_frame = tk.Frame(dialog)
            button_frame.pack(pady=10)
            tk.Button(button_frame, text="Copy to Clipboard", command=copy_to_clipboard).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Exit", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
            
            dialog.mainloop()
            
        except:
            # If even the error dialog fails, fall back to console
            print(f"CRITICAL ERROR: {error_msg}")
            print(tb_str)
            input("Press Enter to exit...")