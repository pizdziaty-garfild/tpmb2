#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TPMB2 - Enhanced Telegram Periodic Message Bot v2.1
Main GUI application for bot management (with templates)
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
import requests
import ssl
from urllib.request import urlopen, Request
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def check_requirements():
    required = [('telegram', 'python-telegram-bot'), ('cryptography', 'cryptography'), 
                ('requests', 'requests'), ('certifi', 'certifi'), ('ntplib', 'ntplib')]
    missing = []
    for module, package in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if missing:
        messagebox.showerror("Missing Dependencies", f"Missing: {', '.join(missing)}")
        return False
    return True

class TPMB2GUI:
    def __init__(self):
        if not check_requirements():
            sys.exit(1)
        from bot.core import TelegramBot
        from utils.config import Config
        from utils.logger import setup_logger
        
        self.root = tk.Tk()
        self.root.title("TPMB2 - Enhanced Bot Manager")
        self.root.geometry("1000x740")
        self.root.minsize(820, 560)
        
        self.bot = None
        self.config = Config()
        self.logger = setup_logger()
        self.bot_thread = None
        self.is_running = False
        
        self._create_ui()
        self._update_status()
        self.root.after(2000, self._periodic_update)

    # ... status/controls/notebook same ...

    def _create_config_tab(self, parent):
        parent.columnconfigure(1, weight=1)
        # Token & Test
        ttk.Label(parent, text="Bot Token:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.token_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.token_var, show="*", width=50).grid(row=0, column=1, sticky=tk.EW, padx=10)
        token_frame = ttk.Frame(parent); token_frame.grid(row=0, column=2)
        ttk.Button(token_frame, text="Save Token", command=self._save_token).pack(side=tk.LEFT)
        ttk.Button(token_frame, text="Test Connection", command=self._test_connection).pack(side=tk.LEFT, padx=(5,0))
        
        # Templates selector
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
        
        # Message editor for active template
        ttk.Label(parent, text="Message (active template):").grid(row=2, column=0, sticky=(tk.W,tk.N), pady=(10,2))
        self.msg_text = scrolledtext.ScrolledText(parent, width=60, height=6)
        self.msg_text.grid(row=2, column=1, columnspan=2, sticky=tk.EW, padx=10, pady=(10,5))
        self.msg_text.insert('1.0', self.config.get_message_text())
        ttk.Button(parent, text="Save Message", command=self._save_message).grid(row=3, column=1, sticky=tk.W, padx=10)
        
        # Proxy panel omitted here for brevity (unchanged)
        self._create_proxy_panel(parent)

    def _reload_templates_into_combo(self):
        keys = self.config.list_templates()
        self.template_combo["values"] = keys
        if self.config.get_active_template_key() not in keys and keys:
            self.template_var.set(keys[0])
        else:
            self.template_var.set(self.config.get_active_template_key())

    def _set_active_template(self):
        key = self.template_var.get().strip()
        self.config.set_active_template_key(key)
        self.msg_text.delete('1.0', tk.END)
        self.msg_text.insert('1.0', self.config.get_message_text())
        messagebox.showinfo("Templates", f"Active template set to: {key}")

    def _new_template(self):
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

    def _delete_template(self):
        key = self.template_var.get().strip()
        if key == self.config.get_active_template_key():
            messagebox.showerror("Templates", "Cannot delete the active template")
            return
        if messagebox.askyesno("Templates", f"Delete template '{key}'?"):
            if self.config.remove_template(key):
                self._reload_templates_into_combo()
                self.msg_text.delete('1.0', tk.END)
                self.msg_text.insert('1.0', self.config.get_message_text())

    # ... rest of GUI: logs, groups, restart, updater with SSL fix ...

