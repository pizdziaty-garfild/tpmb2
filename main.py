#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TPMB2 - Enhanced Bot v2.1 - Multi-Bot Edition with Enhanced UI
Improved tab visibility and per-bot SOCKS5 proxy configurations
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
from utils.scrollable import ScrollableFrame

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def ensure_logs_directory():
    """Ensure logs directory exists"""
    logs_dir = os.path.join(current_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

def check_requirements():
    """Check if all required modules are available"""
    required = [
        ('telegram', 'python-telegram-bot>=20.7'),
        ('cryptography', 'cryptography>=41.0.0'), 
        ('ssl', 'built-in (should be available)'),
        ('tkinter', 'built-in GUI (should be available)'),
    ]
    
    missing = []
    for module, package in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        messagebox.showerror("Missing Dependencies", f"Install: {' '.join(missing)}")
        return False
    return True

class TPMB2GUI:
    def __init__(self):
        try:
            if not check_requirements():
                sys.exit(1)
            
            from bot.core import TelegramBot
            from utils.config import Config
            from utils.logger import setup_logger
            from utils.bots_registry import BotRegistry
            from utils.licensing import LicenseManager
            
            self.root = tk.Tk()
            self.root.title("TPMB2 v2.1 - Multi-Bot Edition")
            self.root.geometry("1150x850")
            self.root.minsize(950, 700)
            
            self._configure_styles()
            
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
            
            self.logger.info("TPMB2 Multi-Bot GUI initialized successfully")
            
        except Exception as e:
            tb_str = traceback.format_exc()
            print(f"CRITICAL ERROR: {e}")
            print(tb_str)
            sys.exit(1)
    
    def _configure_styles(self):
        """Configure enhanced ttk styles for better visibility"""
        style = ttk.Style()
        
        # Enhanced button styles
        style.configure("Accent.TButton", 
                       font=('Arial', 9, 'bold'))
        
        style.configure("Accent.TCheckbutton", 
                       font=('Arial', 9))
        
        # Enhanced tab styling for better visibility
        style.configure("Enhanced.TNotebook.Tab", 
                       padding=(25, 12),
                       font=('Arial', 11, 'bold'))
        
        try:
            style.theme_use('vista')  # Better looking theme if available
        except:
            pass
            
    def _create_ui(self):
        try:
            # Status frame
            status_frame = ttk.LabelFrame(self.root, text="📊 System Status", padding=12)
            status_frame.pack(fill=tk.X, padx=12, pady=8)
            
            self.status_var = tk.StringVar(value="Stopped")
            self.groups_var = tk.StringVar(value="0")
            self.license_var = tk.StringVar(value="❌ No License")
            
            ttk.Label(status_frame, text="Status:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)
            self.status_label = ttk.Label(status_frame, textvariable=self.status_var, font=('Arial', 10, 'bold'))
            self.status_label.grid(row=0, column=1, sticky=tk.W, padx=(5,30))
            
            ttk.Label(status_frame, text="Groups:", font=('Arial', 10, 'bold')).grid(row=0, column=2, sticky=tk.W)
            ttk.Label(status_frame, textvariable=self.groups_var, font=('Arial', 10)).grid(row=0, column=3, padx=(5,30))
            
            ttk.Label(status_frame, text="License:", font=('Arial', 10, 'bold')).grid(row=0, column=4, sticky=tk.W)
            self.license_label = ttk.Label(status_frame, textvariable=self.license_var, font=('Arial', 9, 'bold'))
            self.license_label.grid(row=0, column=5, sticky=tk.W, padx=(5,0))
            
            # Control frame
            ctrl_frame = ttk.LabelFrame(self.root, text="🎮 Bot Control", padding=12)
            ctrl_frame.pack(fill=tk.X, padx=12, pady=8)
            
            self.start_btn = ttk.Button(ctrl_frame, text="▶️ Start Bot", command=self._start_bot, style="Accent.TButton")
            self.start_btn.pack(side=tk.LEFT, padx=(0,10))
            
            self.restart_btn = ttk.Button(ctrl_frame, text="🔄 Restart", command=self._restart_bot, state=tk.DISABLED)
            self.restart_btn.pack(side=tk.LEFT, padx=10)
            
            self.stop_btn = ttk.Button(ctrl_frame, text="⏹️ Stop Bot", command=self._stop_bot, state=tk.DISABLED)
            self.stop_btn.pack(side=tk.LEFT, padx=10)
            
            # Enhanced notebook with better tab visibility
            notebook = ttk.Notebook(self.root, style="Enhanced.TNotebook")
            notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
            
            # Configuration tab (scrollable)
            config_frame = ttk.Frame(notebook)
            notebook.add(config_frame, text="⚙️  Configuration")
            config_scroll = ScrollableFrame(config_frame)
            config_scroll.pack(fill=tk.BOTH, expand=True)
            self._create_config_tab(config_scroll.container)
            
            # Bot Management tab (scrollable) - ENHANCED
            bot_frame = ttk.Frame(notebook)
            notebook.add(bot_frame, text="🤖  Bot Management")
            bot_scroll = ScrollableFrame(bot_frame)
            bot_scroll.pack(fill=tk.BOTH, expand=True)
            self._create_bot_management_tab(bot_scroll.container)
            
            # Logs tab
            logs_frame = ttk.Frame(notebook)
            notebook.add(logs_frame, text="📄  Logs")
            self._create_logs_tab(logs_frame)
            
            # Groups tab (scrollable)
            groups_frame = ttk.Frame(notebook)
            notebook.add(groups_frame, text="📊  Groups")
            groups_scroll = ScrollableFrame(groups_frame)
            groups_scroll.pack(fill=tk.BOTH, expand=True)
            self._create_groups_tab(groups_scroll.container)
            
        except Exception as e:
            self.logger.exception("Error creating UI")
            messagebox.showerror("UI Error", f"Failed to create UI: {e}")
            raise
    
    def _create_bot_management_tab(self, parent):
        """Enhanced Bot Management with per-bot SOCKS5"""
        try:
            parent.columnconfigure(0, weight=1)
            
            # Active Bot Selection
            active_frame = ttk.LabelFrame(parent, text="🤖 Active Bot Selection", padding=15)
            active_frame.pack(fill=tk.X, padx=15, pady=(0,15))
            active_frame.columnconfigure(1, weight=1)
            
            ttk.Label(active_frame, text="Active Bot:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=8)
            self.active_bot_var = tk.StringVar()
            self.bot_combo = ttk.Combobox(active_frame, textvariable=self.active_bot_var, state="readonly", 
                                         width=50, font=('Arial', 9))
            self.bot_combo.grid(row=0, column=1, sticky=tk.EW, padx=(15,0), pady=8)
            self.bot_combo.bind('<<ComboboxSelected>>', self._on_bot_selected)
            
            # Bot buttons
            bot_buttons = ttk.Frame(active_frame)
            bot_buttons.grid(row=1, column=0, columnspan=2, pady=(10,0))
            ttk.Button(bot_buttons, text="✅ Set Active", command=self._set_active_bot, style="Accent.TButton").pack(side=tk.LEFT, padx=(0,10))
            ttk.Button(bot_buttons, text="➕ Add Bot", command=self._add_bot, style="Accent.TButton").pack(side=tk.LEFT, padx=10)
            ttk.Button(bot_buttons, text="➖ Remove", command=self._remove_bot).pack(side=tk.LEFT, padx=10)
            
            # License Management
            license_frame = ttk.LabelFrame(parent, text="🔑 License Management", padding=15)
            license_frame.pack(fill=tk.X, padx=15, pady=(0,15))
            license_frame.columnconfigure(1, weight=1)
            
            ttk.Label(license_frame, text="License Key:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=8)
            self.license_key_var = tk.StringVar()
            ttk.Entry(license_frame, textvariable=self.license_key_var, width=60, 
                     font=('Consolas', 9)).grid(row=0, column=1, sticky=tk.EW, padx=(15,0), pady=8)
            
            license_buttons = ttk.Frame(license_frame)
            license_buttons.grid(row=1, column=0, columnspan=2, pady=(10,0))
            ttk.Button(license_buttons, text="🔍 Validate", command=self._validate_license, style="Accent.TButton").pack(side=tk.LEFT, padx=(0,10))
            ttk.Button(license_buttons, text="✅ Activate", command=self._activate_license, style="Accent.TButton").pack(side=tk.LEFT, padx=10)
            ttk.Button(license_buttons, text="🎯 Generate", command=self._generate_license, style="Accent.TButton").pack(side=tk.LEFT, padx=10)
            
            # Per-Bot SOCKS5 Proxy (MOVED FROM CONFIG)
            proxy_frame = ttk.LabelFrame(parent, text="🔗 SOCKS5 Proxy (Per-Bot)", padding=15)
            proxy_frame.pack(fill=tk.X, padx=15, pady=(0,15))
            proxy_frame.columnconfigure(1, weight=1)
            
            self.proxy_enabled_var = tk.BooleanVar()
            self.proxy_host_var = tk.StringVar()
            self.proxy_port_var = tk.StringVar()
            self.proxy_username_var = tk.StringVar()
            self.proxy_password_var = tk.StringVar()
            
            ttk.Checkbutton(proxy_frame, text="✅ Enable SOCKS5 Proxy for this bot", 
                          variable=self.proxy_enabled_var, style="Accent.TCheckbutton").grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0,12))
            
            # Proxy grid
            ttk.Label(proxy_frame, text="Host:", font=('Arial', 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
            ttk.Entry(proxy_frame, textvariable=self.proxy_host_var, width=20, font=('Arial', 9)).grid(row=1, column=1, sticky=tk.W, padx=(10,0), pady=8)
            
            ttk.Label(proxy_frame, text="Port:", font=('Arial', 10)).grid(row=1, column=2, sticky=tk.W, padx=(25,8), pady=8)
            ttk.Entry(proxy_frame, textvariable=self.proxy_port_var, width=8, font=('Arial', 9)).grid(row=1, column=3, sticky=tk.W, pady=8)
            
            ttk.Label(proxy_frame, text="Username:", font=('Arial', 10)).grid(row=2, column=0, sticky=tk.W, pady=8)
            ttk.Entry(proxy_frame, textvariable=self.proxy_username_var, width=20, font=('Arial', 9)).grid(row=2, column=1, sticky=tk.W, padx=(10,0), pady=8)
            
            ttk.Label(proxy_frame, text="Password:", font=('Arial', 10)).grid(row=2, column=2, sticky=tk.W, padx=(25,8), pady=8)
            ttk.Entry(proxy_frame, textvariable=self.proxy_password_var, show="*", width=20, font=('Arial', 9)).grid(row=2, column=3, sticky=tk.W, pady=8)
            
            # Proxy buttons
            proxy_buttons = ttk.Frame(proxy_frame)
            proxy_buttons.grid(row=3, column=0, columnspan=4, pady=(15,0))
            ttk.Button(proxy_buttons, text="✅ Save Proxy", command=self._save_bot_proxy, style="Accent.TButton").pack(side=tk.LEFT, padx=(0,10))
            ttk.Button(proxy_buttons, text="🔍 Test Connection", command=self._test_bot_proxy).pack(side=tk.LEFT, padx=10)
            
            # Bot Info Display
            info_frame = ttk.LabelFrame(parent, text="📄 Bot Information", padding=15)
            info_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0,15))
            
            self.bot_info_text = scrolledtext.ScrolledText(info_frame, height=12, wrap=tk.WORD, font=('Consolas', 9))
            self.bot_info_text.pack(fill=tk.BOTH, expand=True)
            
            # Initialize
            self._refresh_bot_list()
            
        except Exception as e:
            self.logger.exception("Error creating bot management tab")
            messagebox.showerror("Bot Management Error", f"Failed to create tab: {e}")
    
    def _create_config_tab(self, parent):
        """Simplified config tab - proxy moved to Bot Management"""
        try:
            parent.columnconfigure(0, weight=1)
            
            # Token section
            token_frame = ttk.LabelFrame(parent, text="🔐 Bot Token Configuration", padding=15)
            token_frame.pack(fill=tk.X, padx=15, pady=(0,15))
            token_frame.columnconfigure(1, weight=1)
            
            ttk.Label(token_frame, text="Bot Token:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=8)
            self.token_var = tk.StringVar()
            ttk.Entry(token_frame, textvariable=self.token_var, show="*", width=50, font=('Consolas', 9)).grid(row=0, column=1, sticky=tk.EW, padx=15, pady=8)
            
            token_buttons = ttk.Frame(token_frame)
            token_buttons.grid(row=1, column=0, columnspan=2, pady=(10,0))
            ttk.Button(token_buttons, text="✅ Save Token", command=self._save_token, style="Accent.TButton").pack(side=tk.LEFT, padx=(0,10))
            ttk.Button(token_buttons, text="🔍 Test Connection", command=self._test_connection).pack(side=tk.LEFT)
            
            # Templates section
            templates_frame = ttk.LabelFrame(parent, text="📝 Message Templates", padding=15)
            templates_frame.pack(fill=tk.X, padx=15, pady=(0,15))
            templates_frame.columnconfigure(1, weight=1)
            
            ttk.Label(templates_frame, text="Active Template:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=8)
            self.template_var = tk.StringVar(value=self.config.get_active_template_key())
            self.template_combo = ttk.Combobox(templates_frame, textvariable=self.template_var, state="readonly", font=('Arial', 9))
            self._reload_templates_into_combo()
            self.template_combo.grid(row=0, column=1, sticky=tk.EW, padx=(15,0), pady=8)
            
            template_buttons = ttk.Frame(templates_frame)
            template_buttons.grid(row=1, column=0, columnspan=2, pady=(10,0))
            ttk.Button(template_buttons, text="✅ Set Active", command=self._set_active_template, style="Accent.TButton").pack(side=tk.LEFT, padx=(0,10))
            ttk.Button(template_buttons, text="➕ New", command=self._new_template).pack(side=tk.LEFT, padx=10)
            ttk.Button(template_buttons, text="➖ Delete", command=self._delete_template).pack(side=tk.LEFT, padx=10)
            
            # Message editor
            editor_frame = ttk.LabelFrame(parent, text="✏️ Message Editor", padding=15)
            editor_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0,15))
            
            ttk.Label(editor_frame, text="Message Text:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0,8))
            self.msg_text = scrolledtext.ScrolledText(editor_frame, height=8, font=('Arial', 10))
            self.msg_text.pack(fill=tk.BOTH, expand=True, pady=(0,15))
            self.msg_text.insert('1.0', self.config.get_message_text())
            
            ttk.Button(editor_frame, text="✅ Save Message", command=self._save_message, style="Accent.TButton").pack(anchor=tk.W)
            
        except Exception as e:
            self.logger.exception("Error creating config tab")
    
    def _create_logs_tab(self, parent):
        try:
            parent.columnconfigure(0, weight=1)
            parent.rowconfigure(1, weight=1)
            
            # Controls
            ctrl_frame = ttk.LabelFrame(parent, text="📄 Log Management", padding=12)
            ctrl_frame.pack(fill=tk.X, padx=12, pady=(8,15))
            
            ttk.Button(ctrl_frame, text="🔄 Refresh", command=self._refresh_logs, style="Accent.TButton").pack(side=tk.LEFT, padx=(0,10))
            ttk.Button(ctrl_frame, text="🗑️ Clear", command=self._clear_logs).pack(side=tk.LEFT, padx=10)
            ttk.Button(ctrl_frame, text="📂 Open Folder", command=self._open_logs_folder).pack(side=tk.LEFT, padx=10)
            
            # Logs display
            logs_frame = ttk.LabelFrame(parent, text="📃 Recent Entries", padding=8)
            logs_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,12))
            
            self.logs_text = scrolledtext.ScrolledText(logs_frame, wrap=tk.WORD, font=('Consolas', 9))
            self.logs_text.pack(fill=tk.BOTH, expand=True)
            self._refresh_logs()
            
        except Exception as e:
            self.logger.exception("Error creating logs tab")
    
    def _create_groups_tab(self, parent):
        try:
            parent.columnconfigure(0, weight=1)
            
            # Single add
            single_frame = ttk.LabelFrame(parent, text="➕ Add Single Group", padding=15)
            single_frame.pack(fill=tk.X, padx=15, pady=(0,15))
            
            controls = ttk.Frame(single_frame)
            controls.pack(fill=tk.X)
            
            ttk.Label(controls, text="Group ID:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
            self.group_var = tk.StringVar()
            ttk.Entry(controls, textvariable=self.group_var, width=20, font=('Arial', 10)).pack(side=tk.LEFT, padx=(10,0))
            
            ttk.Label(controls, text="Name:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(15,10))
            self.group_name_var = tk.StringVar()
            ttk.Entry(controls, textvariable=self.group_name_var, width=25, font=('Arial', 10)).pack(side=tk.LEFT, padx=(0,15))
            
            ttk.Button(controls, text="✅ Add", command=self._add_group, style="Accent.TButton").pack(side=tk.LEFT)
            
            # Bulk area
            bulk_frame = ttk.LabelFrame(parent, text="📁 Bulk Import", padding=15)
            bulk_frame.pack(fill=tk.X, padx=15, pady=(0,15))
            
            self.bulk_groups_text = scrolledtext.ScrolledText(bulk_frame, height=6, font=('Arial', 10))
            self.bulk_groups_text.pack(fill=tk.X, pady=(0,15))
            
            bulk_buttons = ttk.Frame(bulk_frame)
            bulk_buttons.pack(anchor=tk.W)
            ttk.Button(bulk_buttons, text="✅ Add Bulk", command=self._add_bulk_groups, style="Accent.TButton").pack(side=tk.LEFT, padx=(0,10))
            ttk.Button(bulk_buttons, text="🗑️ Clear", command=lambda: self.bulk_groups_text.delete('1.0', tk.END)).pack(side=tk.LEFT, padx=10)
            
            # Groups list
            list_frame = ttk.LabelFrame(parent, text="📋 Groups List", padding=15)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0,15))
            
            self.groups_list = tk.Listbox(list_frame, font=('Arial', 9))
            self.groups_list.pack(fill=tk.BOTH, expand=True)
            
            self._refresh_groups()
            
        except Exception as e:
            self.logger.exception("Error creating groups tab")
    
    # Bot Management methods
    def _refresh_bot_list(self):
        try:
            bots = self.registry.list_bots()
            active_bot = self.registry.get_active_bot()
            
            if not bots:
                display_bots = ["(create first bot)"]
            else:
                display_bots = []
                for bot_id in bots:
                    bot_data = self.registry.get_bot(bot_id)
                    name = bot_data.get('name', bot_id)
                    status = bot_data.get('license_status', 'inactive')
                    proxy = bot_data.get('proxy_config', {}).get('enabled', False)
                    
                    lic = "✅" if status == 'active' else "❌"
                    prx = "🔗" if proxy else "🚫"
                    
                    display_bots.append(f"{lic}{prx} {name} ({bot_id})")
            
            self.bot_combo['values'] = display_bots
            
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
        try:
            active_bot = self.registry.get_active_bot()
            
            if not active_bot:
                info = "🚀 Welcome to TPMB2 Multi-Bot!\n\nNo active bot selected.\n\n👉 Steps:\n1. Add Bot\n2. Set License\n3. Configure Proxy\n4. Start Bot"
                self.bot_info_text.delete('1.0', tk.END)
                self.bot_info_text.insert('1.0', info)
                return
            
            bot_data = self.registry.get_bot(active_bot)
            proxy_config = self.registry.get_bot_proxy_config(active_bot)
            
            # License info
            license_key = bot_data.get('license_key', '')
            license_status = "No license"
            if license_key:
                try:
                    token = self.config.get_bot_token()
                    status = self.licenser.validate_key(license_key, bot_token=token or "DUMMY", hwid=self.licenser.get_hwid())
                    license_status = "✅ Active" if status.get('valid') else "❌ Invalid"
                except:
                    license_status = "❌ Error"
            
            # Proxy info
            proxy_status = "Disabled"
            if proxy_config.get('enabled'):
                proxy_status = f"Enabled - {proxy_config.get('host')}:{proxy_config.get('port')}"
            
            info = f"""🤖 BOT DETAILS
{'='*40}

🆔 ID: {active_bot}
📝 Name: {bot_data.get('name', 'Unnamed')}
📅 Created: {bot_data.get('created_date', 'Unknown')}

🔑 LICENSE
{'-'*20}
Status: {license_status}
Key: {license_key[:30] + '...' if len(license_key) > 30 else license_key or 'Not set'}

🔗 PROXY
{'-'*20}
Status: {proxy_status}

📊 STATS
{'-'*20}
Groups: {len(self.config.get_groups())}
Running: {'Yes ▶️' if self.is_running else 'No ⏹️'}
"""
            
            self.bot_info_text.delete('1.0', tk.END)
            self.bot_info_text.insert('1.0', info)
            
        except Exception as e:
            self.logger.exception("Error updating bot info")
    
    def _on_bot_selected(self, event=None):
        try:
            selection = self.bot_combo.get()
            if not selection or "(create first bot)" in selection:
                return
            
            if "(" in selection and selection.endswith(")"):
                bot_id = selection.split("(")[-1].rstrip(")")
                
                # Load bot data
                bot_data = self.registry.get_bot(bot_id)
                self.license_key_var.set(bot_data.get('license_key', ''))
                
                # Load proxy config
                proxy_config = self.registry.get_bot_proxy_config(bot_id)
                self.proxy_enabled_var.set(proxy_config.get("enabled", False))
                self.proxy_host_var.set(proxy_config.get("host", "127.0.0.1"))
                self.proxy_port_var.set(str(proxy_config.get("port", 1080)))
                self.proxy_username_var.set(proxy_config.get("username", ""))
                self.proxy_password_var.set("")
                
                self._update_bot_info()
                
        except Exception as e:
            self.logger.exception("Error handling bot selection")
    
    def _add_bot(self):
        try:
            bot_id = simpledialog.askstring("Add Bot", "Bot ID:", parent=self.root)
            if not bot_id:
                return
                
            if bot_id in self.registry.list_bots():
                messagebox.showerror("Error", "Bot already exists!")
                return
                
            name = simpledialog.askstring("Add Bot", "Display Name:", parent=self.root, initialvalue=bot_id)
            if not name:
                name = bot_id
            
            if self.registry.add_bot(bot_id, name):
                self._refresh_bot_list()
                messagebox.showinfo("Success", f"Bot '{bot_id}' added!")
            else:
                messagebox.showerror("Error", "Failed to add bot")
                
        except Exception as e:
            messagebox.showerror("Error", f"Add bot failed: {e}")
    
    def _remove_bot(self):
        try:
            active_bot = self.registry.get_active_bot()
            if not active_bot:
                messagebox.showwarning("Warning", "No bot selected")
                return
                
            if messagebox.askyesno("Confirm", f"Remove bot '{active_bot}'?"):
                if self.registry.remove_bot(active_bot):
                    self._refresh_bot_list()
                    messagebox.showinfo("Success", "Bot removed")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Remove failed: {e}")
    
    def _set_active_bot(self):
        try:
            selection = self.bot_combo.get()
            if not selection or "(create first bot)" in selection:
                return
            
            if "(" in selection and selection.endswith(")"):
                bot_id = selection.split("(")[-1].rstrip(")")
                if self.registry.set_active_bot(bot_id):
                    self._refresh_bot_list()
                    messagebox.showinfo("Success", f"Active bot: {bot_id}")
                    
                    if self.is_running:
                        if messagebox.askyesno("Restart", "Restart bot with new settings?"):
                            self._restart_bot()
                            
        except Exception as e:
            messagebox.showerror("Error", f"Set active failed: {e}")
    
    def _save_bot_proxy(self):
        try:
            active_bot = self.registry.get_active_bot()
            if not active_bot:
                messagebox.showerror("Error", "No active bot")
                return
                
            port = int(self.proxy_port_var.get()) if self.proxy_port_var.get() else 1080
            
            if self.registry.set_bot_proxy_config(
                bot_id=active_bot,
                enabled=self.proxy_enabled_var.get(),
                host=self.proxy_host_var.get() or "127.0.0.1",
                port=port,
                username=self.proxy_username_var.get(),
                password=self.proxy_password_var.get()
            ):
                self.proxy_password_var.set("")
                messagebox.showinfo("Success", f"Proxy saved for {active_bot}!")
                self._refresh_bot_list()
                self._update_bot_info()
            else:
                messagebox.showerror("Error", "Failed to save proxy")
                
        except Exception as e:
            messagebox.showerror("Error", f"Save proxy failed: {e}")
    
    def _test_bot_proxy(self):
        try:
            active_bot = self.registry.get_active_bot()
            if not active_bot:
                messagebox.showerror("Error", "No active bot")
                return
                
            proxy_config = self.registry.get_bot_proxy_config(active_bot)
            if proxy_config.get('enabled'):
                info = f"Proxy for {active_bot}:\n\nHost: {proxy_config.get('host')}\nPort: {proxy_config.get('port')}\nUsername: {proxy_config.get('username') or '(none)'}"
                messagebox.showinfo("Proxy Test", info)
            else:
                messagebox.showinfo("Proxy Test", f"Proxy disabled for {active_bot}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Test failed: {e}")
    
    # License methods (simplified)
    def _validate_license(self):
        try:
            key = self.license_key_var.get().strip()
            if not key:
                messagebox.showwarning("Warning", "Enter license key")
                return
                
            token = self.config.get_bot_token()
            if not token:
                messagebox.showerror("Error", "No bot token configured")
                return
                
            status = self.licenser.validate_key(key, bot_token=token, hwid=self.licenser.get_hwid())
            
            if status.get('valid'):
                messagebox.showinfo("Valid", f"✅ License valid! Expires: 20{status.get('expires')}")
            else:
                messagebox.showerror("Invalid", f"❌ License invalid: {status.get('reason')}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Validation failed: {e}")
    
    def _activate_license(self):
        try:
            key = self.license_key_var.get().strip()
            active_bot = self.registry.get_active_bot()
            
            if not key or not active_bot:
                messagebox.showwarning("Warning", "Enter key and select bot")
                return
                
            result = self.registry.set_license(active_bot, key)
            if result.get('ok'):
                messagebox.showinfo("Success", f"✅ License activated for {active_bot}!")
                self._refresh_bot_list()
                self._update_bot_info()
            else:
                messagebox.showerror("Failed", "❌ License activation failed")
                
        except Exception as e:
            messagebox.showerror("Error", f"Activation failed: {e}")
    
    def _generate_license(self):
        try:
            from utils.licensing import LicenseManager
            lm = LicenseManager()
            token = self.config.get_bot_token()
            
            if not token:
                messagebox.showerror("Error", "Configure bot token first")
                return
                
            days = simpledialog.askinteger("Generate License", "Valid for how many days?", initialvalue=365, minvalue=1)
            if not days:
                return
                
            key = lm.generate_key(bot_token=token, days_valid=days, hwid=lm.get_hwid())
            self.license_key_var.set(key)
            
            # Copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(key)
            
            messagebox.showinfo("Generated", f"License generated and copied to clipboard!\n\nValid for: {days} days")
            
        except Exception as e:
            messagebox.showerror("Error", f"Generation failed: {e}")
    
    # Basic methods
    def _save_token(self):
        try:
            token = self.token_var.get().strip()
            if token:
                self.config.set_bot_token(token)
                self.token_var.set("")
                messagebox.showinfo("Success", "Token saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")
    
    def _test_connection(self):
        messagebox.showinfo("Test", "Connection test - check logs for details")
    
    def _save_message(self):
        try:
            msg = self.msg_text.get('1.0', tk.END).strip()
            if msg:
                self.config.set_message_text(msg)
                messagebox.showinfo("Success", "Message saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")
    
    def _add_group(self):
        try:
            gid = self.group_var.get().strip()
            name = self.group_name_var.get().strip()
            if gid:
                if self.config.add_group(int(gid), name or None):
                    self.group_var.set("")
                    self.group_name_var.set("")
                    self._refresh_groups()
                    messagebox.showinfo("Success", "Group added!")
        except Exception as e:
            messagebox.showerror("Error", f"Add failed: {e}")
    
    def _add_bulk_groups(self):
        try:
            text = self.bulk_groups_text.get('1.0', tk.END)
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            added = 0
            for line in lines:
                try:
                    if ';' in line:
                        gid, name = line.split(';', 1)
                        if self.config.add_group(int(gid.strip()), name.strip()):
                            added += 1
                    else:
                        if self.config.add_group(int(line)):
                            added += 1
                except:
                    continue
            self._refresh_groups()
            messagebox.showinfo("Success", f"Added {added} groups!")
        except Exception as e:
            messagebox.showerror("Error", f"Bulk add failed: {e}")
    
    def _refresh_groups(self):
        try:
            self.groups_list.delete(0, tk.END)
            groups = self.config.get_groups_objects()
            for group in groups:
                gid = group["id"]
                name = group.get("name", "(no name)")
                self.groups_list.insert(tk.END, f"{gid} — {name}")
        except Exception as e:
            self.logger.exception("Error refreshing groups")
    
    def _refresh_logs(self):
        try:
            log_path = os.path.join("logs", "bot.log")
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-100:]  # Last 100 lines
                    content = ''.join(lines)
            else:
                content = "No logs yet. Start bot to see logs."
            
            self.logs_text.delete('1.0', tk.END)
            self.logs_text.insert('1.0', content)
            self.logs_text.see(tk.END)
        except Exception as e:
            self.logs_text.delete('1.0', tk.END)
            self.logs_text.insert('1.0', f"Error loading logs: {e}")
    
    def _clear_logs(self):
        try:
            if messagebox.askyesno("Confirm", "Clear all logs?"):
                for log_file in ["bot.log", "error.log"]:
                    log_path = os.path.join("logs", log_file)
                    if os.path.exists(log_path):
                        open(log_path, 'w').close()
                self._refresh_logs()
                messagebox.showinfo("Success", "Logs cleared!")
        except Exception as e:
            messagebox.showerror("Error", f"Clear failed: {e}")
    
    def _open_logs_folder(self):
        try:
            logs_dir = os.path.join(os.getcwd(), "logs")
            if os.path.exists(logs_dir):
                os.startfile(logs_dir)  # Windows
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open: {e}")
    
    # Template methods (simplified)
    def _reload_templates_into_combo(self):
        try:
            keys = self.config.list_templates()
            self.template_combo["values"] = keys
            if keys:
                self.template_var.set(keys[0])
        except:
            pass
    
    def _set_active_template(self):
        try:
            key = self.template_var.get()
            self.config.set_active_template_key(key)
            self.msg_text.delete('1.0', tk.END)
            self.msg_text.insert('1.0', self.config.get_message_text())
            messagebox.showinfo("Success", f"Template set: {key}")
        except Exception as e:
            messagebox.showerror("Error", f"Set template failed: {e}")
    
    def _new_template(self):
        try:
            key = simpledialog.askstring("New Template", "Template name:", parent=self.root)
            if key and key not in self.config.list_templates():
                self.config.set_template(key, "New template: {timestamp}")
                self._reload_templates_into_combo()
                messagebox.showinfo("Success", f"Template '{key}' created!")
        except Exception as e:
            messagebox.showerror("Error", f"Create failed: {e}")
    
    def _delete_template(self):
        try:
            key = self.template_var.get()
            if messagebox.askyesno("Confirm", f"Delete template '{key}'?"):
                self.config.remove_template(key)
                self._reload_templates_into_combo()
                messagebox.showinfo("Success", "Template deleted!")
        except Exception as e:
            messagebox.showerror("Error", f"Delete failed: {e}")
    
    # Bot control methods
    def _start_bot(self):
        try:
            if self.is_running:
                messagebox.showinfo("Info", "Bot already running")
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
            messagebox.showinfo("Started", "Bot started! Check logs.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Start failed: {e}")
    
    def _restart_bot(self):
        try:
            if not self.is_running:
                self._start_bot()
                return
                
            self.status_var.set("Restarting...")
            if self.bot:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.bot.restart_messaging())
                loop.close()
            messagebox.showinfo("Restarted", "Bot restarted!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Restart failed: {e}")
    
    def _stop_bot(self):
        try:
            if self.bot:
                asyncio.run_coroutine_threadsafe(self.bot.shutdown(), asyncio.get_event_loop())
            self._bot_stopped()
        except Exception as e:
            self._bot_stopped()
    
    def _run_bot_async(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.bot.run())
        except Exception as e:
            self.logger.exception("Bot error")
        finally:
            self.root.after(0, self._bot_stopped)
    
    def _bot_stopped(self):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.restart_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Stopped")
    
    # Status and updates
    def _update_status(self):
        try:
            groups_count = len(self.config.get_groups())
            self.groups_var.set(str(groups_count))
            
            # License status
            active_bot = self.registry.get_active_bot()
            if active_bot:
                bot_data = self.registry.get_bot(active_bot)
                license_key = bot_data.get('license_key', '')
                if license_key:
                    try:
                        token = self.config.get_bot_token()
                        status = self.licenser.validate_key(license_key, bot_token=token or "DUMMY", hwid=self.licenser.get_hwid())
                        if status.get('valid'):
                            self.license_var.set("✅ Active")
                            self.license_label.config(foreground="green")
                        else:
                            self.license_var.set("❌ Invalid")
                            self.license_label.config(foreground="red")
                    except:
                        self.license_var.set("❌ Error")
                        self.license_label.config(foreground="red")
                else:
                    self.license_var.set("❌ No License")
                    self.license_label.config(foreground="red")
            else:
                self.license_var.set("❌ No Bot")
                self.license_label.config(foreground="red")
            
            if self.is_running:
                self.status_var.set("Running")
                self.status_label.config(foreground="green")
            else:
                self.status_var.set("Stopped")
                self.status_label.config(foreground="red")
                
        except Exception as e:
            self.logger.exception("Error updating status")
    
    def _periodic_update(self):
        try:
            self._update_status()
            self.root.after(5000, self._periodic_update)
        except Exception as e:
            self.root.after(10000, self._periodic_update)
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.root.destroy())
        self.root.mainloop()

if __name__ == "__main__":
    try:
        ensure_logs_directory()
        app = TPMB2GUI()
        app.run()
    except Exception as e:
        print(f"CRITICAL: {e}")
        input("Press Enter...")
