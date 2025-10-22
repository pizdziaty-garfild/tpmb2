#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TPMB2 - Enhanced Telegram Periodic Message Bot v2.0
Main GUI application for bot management
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
from urllib.request import urlopen, Request
from datetime import datetime

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def check_requirements():
    """Check if all required modules are available"""
    required = [('telegram', 'python-telegram-bot'), ('cryptography', 'cryptography'), 
                ('requests', 'requests'), ('certifi', 'certifi'), ('ntplib', 'ntplib')]
    missing = []
    for module, package in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if missing:
        error_msg = f"""Missing modules: {', '.join(missing)}

Run installer: install_tpmb2.bat
or install manually: pip install {' '.join(missing)}"""
        messagebox.showerror("Missing Dependencies", error_msg)
        return False
    return True

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
        if not check_requirements():
            sys.exit(1)
        
        # Import after requirements check
        from bot.core import TelegramBot
        from utils.config import Config
        from utils.logger import setup_logger
        
        self.root = tk.Tk()
        self.root.title("TPMB2 - Enhanced Bot Manager")
        self.root.geometry("1000x720")
        self.root.minsize(800, 550)
        
        self.bot = None
        self.config = Config()
        self.logger = setup_logger()
        self.bot_thread = None
        self.is_running = False
        
        self._create_ui()
        self._update_status()
        self.root.after(2000, self._periodic_update)
    
    def _create_ui(self):
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
        
        # Status frame
        status_frame = ttk.LabelFrame(self.root, text="Status", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_var = tk.StringVar(value="Stopped")
        self.groups_var = tk.StringVar(value="0")
        self.interval_var = tk.StringVar(value=str(self.config.get_interval_minutes()))
        
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky=tk.W)
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, font=('Arial', 9, 'bold'))
        self.status_label.grid(row=0, column=1, sticky=tk.W, padx=(5,20))
        
        ttk.Label(status_frame, text="Groups:").grid(row=0, column=2, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.groups_var).grid(row=0, column=3, sticky=tk.W, padx=(5,0))
        
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
        
        # Config tab
        config_tab = ttk.Frame(notebook)
        notebook.add(config_tab, text="Configuration")
        self._create_config_tab(config_tab)
        
        # Logs tab
        logs_tab = ttk.Frame(notebook)
        notebook.add(logs_tab, text="Logs")
        self._create_logs_tab(logs_tab)
        
        # Groups tab
        groups_tab = ttk.Frame(notebook)
        notebook.add(groups_tab, text="Groups")
        self._create_groups_tab(groups_tab)
    
    def _create_config_tab(self, parent):
        parent.columnconfigure(1, weight=1)
        
        # Token
        ttk.Label(parent, text="Bot Token:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.token_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.token_var, show="*", width=50).grid(row=0, column=1, sticky=tk.EW, padx=10)
        token_frame = ttk.Frame(parent)
        token_frame.grid(row=0, column=2)
        ttk.Button(token_frame, text="Save Token", command=self._save_token).pack(side=tk.LEFT)
        ttk.Button(token_frame, text="Test Connection", command=self._test_connection).pack(side=tk.LEFT, padx=(5,0))
        
        # Message
        ttk.Label(parent, text="Message:").grid(row=1, column=0, sticky=(tk.W,tk.N), pady=(10,2))
        self.msg_text = scrolledtext.ScrolledText(parent, width=60, height=6)
        self.msg_text.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=10, pady=(10,5))
        self.msg_text.insert('1.0', self.config.get_message_text())
        
        ttk.Button(parent, text="Save Message", command=self._save_message).grid(row=2, column=1, sticky=tk.W, padx=10)
        
        # Proxy section
        proxy_frame = ttk.LabelFrame(parent, text="SOCKS5 Proxy", padding=10)
        proxy_frame.grid(row=3, column=0, columnspan=3, sticky=tk.EW, padx=10, pady=(20,0))
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
        
        ttk.Button(proxy_frame, text="Save Proxy Config", command=self._save_proxy_config).grid(row=3, column=0, pady=(10,0))
        
    def _create_logs_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        
        # Controls
        ctrl_frame = ttk.Frame(parent)
        ctrl_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0,10))
        ttk.Button(ctrl_frame, text="Refresh", command=self._refresh_logs).grid(row=0, column=0)
        ttk.Button(ctrl_frame, text="Clear", command=self._clear_logs).grid(row=0, column=1, padx=(10,0))
        
        # Logs display
        self.logs_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, font=('Consolas', 9))
        self.logs_text.grid(row=1, column=0, sticky=(tk.W,tk.E,tk.N,tk.S))
        self._refresh_logs()
    
    def _create_groups_tab(self, parent):
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
    
    def _load_proxy_config(self):
        proxy_config = self.config.get_proxy_config()
        self.proxy_enabled_var.set(proxy_config.get("enabled", False))
        self.proxy_host_var.set(proxy_config.get("host", "127.0.0.1"))
        self.proxy_port_var.set(str(proxy_config.get("port", 1080)))
        self.proxy_username_var.set(proxy_config.get("username", ""))
        # Don't load password for security
        
    def _save_proxy_config(self):
        try:
            port = int(self.proxy_port_var.get())
            if port < 1 or port > 65535:
                raise ValueError("Port must be 1-65535")
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
            return
        
        self.config.set_proxy_config(
            enabled=self.proxy_enabled_var.get(),
            host=self.proxy_host_var.get(),
            port=port,
            username=self.proxy_username_var.get(),
            password=self.proxy_password_var.get()
        )
        self.proxy_password_var.set("")  # Clear password field
        messagebox.showinfo("Success", "Proxy configuration saved!")
        self._suggest_restart("Proxy configuration changed")
        
    def _test_connection(self):
        """Test connection to Telegram API (with proxy if enabled)"""
        try:
            self.root.config(cursor="watch")
            self.root.update()
            
            from bot.security import SecurityManager
            security = SecurityManager()
            
            # Test basic connectivity
            if security.verify_telegram_api():
                messagebox.showinfo("Connection Test", "✅ Connection to Telegram API successful!\n\n" + 
                                   ("Using proxy" if self.config.get_proxy_config().get("enabled") else "Direct connection"))
            else:
                messagebox.showerror("Connection Test", "❌ Failed to connect to Telegram API")
                
        except Exception as e:
            messagebox.showerror("Connection Test", f"❌ Connection test failed:\n{e}")
        finally:
            self.root.config(cursor="")
    
    def _suggest_restart(self, reason: str):
        """Suggest restart after configuration changes"""
        if self.is_running:
            if messagebox.askyesno("Restart Recommended", f"{reason}.\n\nRestart bot to apply changes?"):
                self._restart_bot()
                
    def _start_bot(self):
        if self.is_running:
            messagebox.showinfo("Info", "Bot is already running")
            return
        
        if not self.config.get_bot_token():
            messagebox.showerror("Error", "Configure bot token first!")
            return
        
        try:
            from bot.core import TelegramBot
            self.bot = TelegramBot()
            self.bot_thread = threading.Thread(target=self._run_bot_async, daemon=True)
            self.bot_thread.start()
            
            self.is_running = True
            self.start_btn.config(state=tk.DISABLED)
            self.restart_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
            self.status_var.set("Starting...")
            messagebox.showinfo("Started", "Bot started in background. Use /start command in Telegram to begin messaging.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start bot: {e}")
    
    def _restart_bot(self):
        """Graceful restart without closing GUI"""
        if not self.is_running:
            messagebox.showinfo("Info", "Bot is not running. Use Start instead.")
            return
        
        try:
            self.status_var.set("Restarting...")
            self.root.update()
            
            # Restart messaging in bot instance
            if self.bot:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.bot.restart_messaging())
                loop.close()
            
            messagebox.showinfo("Restarted", "Bot restarted successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to restart bot: {e}")
            self._bot_stopped()
    
    def _run_bot_async(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.bot.run())
        except Exception as e:
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
    
    def _stop_bot(self):
        if not self.is_running:
            return
        try:
            if self.bot:
                asyncio.run_coroutine_threadsafe(self.bot.shutdown(), asyncio.get_event_loop())
            self._bot_stopped()
        except:
            self._bot_stopped()
    
    def _save_token(self):
        token = self.token_var.get().strip()
        if not token:
            messagebox.showerror("Error", "Enter bot token!")
            return
        self.config.set_bot_token(token)
        self.token_var.set("")
        messagebox.showinfo("Success", "Token saved and encrypted!")
        # Token change requires manual restart
        if self.is_running:
            messagebox.showwarning("Restart Required", "Token changed. Please STOP and START the bot manually.")
    
    def _save_message(self):
        msg = self.msg_text.get('1.0', tk.END).strip()
        if not msg:
            messagebox.showerror("Error", "Message cannot be empty!")
            return
        self.config.set_message_text(msg)
        messagebox.showinfo("Success", "Message saved!")
        self._suggest_restart("Message changed")
    
    def _update_interval(self, event=None):
        try:
            interval = int(self.interval_var.get())
            if interval < 1:
                raise ValueError("Interval must be > 0")
            self.config.set_interval_minutes(interval)
            messagebox.showinfo("Success", f"Global interval set to {interval} minutes")
            self._suggest_restart("Global interval changed")
        except ValueError:
            messagebox.showerror("Error", "Enter valid number of minutes!")
            self.interval_var.set(str(self.config.get_interval_minutes()))
    
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
                self._suggest_restart("Group added")
            else:
                messagebox.showwarning("Duplicate", f"Group {gid} already exists!")
        except Exception:
            messagebox.showerror("Error", "Invalid Group ID!")
    
    def _add_bulk_groups(self):
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
        if added > 0:
            self._suggest_restart("Groups added")
    
    def _edit_selected_group(self):
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
                self._suggest_restart("Group updated")
    
    def _deduplicate_groups(self):
        removed = self.config.deduplicate_groups()
        if removed > 0:
            self._refresh_groups()
            self._update_status()
            messagebox.showinfo("Deduplicate", f"Removed {removed} duplicate groups")
            self._suggest_restart("Groups deduplicated")
        else:
            messagebox.showinfo("Deduplicate", "No duplicates found")
    
    def _remove_group(self):
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
            self._suggest_restart("Group removed")
    
    def _refresh_groups(self):
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
            self.logs_text.delete('1.0', tk.END)
            self.logs_text.insert('1.0', f"Error loading logs: {e}")
    
    def _clear_logs(self):
        if messagebox.askyesno("Confirm", "Clear all logs?"):
            try:
                for log_file in ["bot.log", "error.log"]:
                    log_path = os.path.join("logs", log_file)
                    if os.path.exists(log_path):
                        open(log_path, 'w').close()
                self._refresh_logs()
                messagebox.showinfo("Success", "Logs cleared!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear logs: {e}")
    
    def _update_status(self):
        groups_count = len(self.config.get_groups())
        self.groups_var.set(str(groups_count))
        
        if self.is_running:
            self.status_var.set("Running")
        else:
            self.status_var.set("Stopped")
    
    def _periodic_update(self):
        self._update_status()
        self.root.after(5000, self._periodic_update)
    
    def _on_close(self):
        if self.is_running:
            if messagebox.askyesno("Confirm", "Bot is running. Stop and exit?"):
                self._stop_bot()
                self.root.after(1000, self.root.destroy)
        else:
            self.root.destroy()
    
    def _safe_update_from_github(self):
        """Simple updater: fetches latest main.zip from GitHub tpmb2 repo and replaces files safely."""
        try:
            if not messagebox.askyesno("Update", "Download and apply latest update from GitHub?\nConfig and logs will be preserved."):
                return
            zip_url = "https://codeload.github.com/pizdziaty-garfild/tpmb2/zip/refs/heads/main"
            req = Request(zip_url, headers={"User-Agent":"TPMB2-Updater"})
            self.root.config(cursor="watch"); self.root.update()
            with urlopen(req, timeout=30) as resp:
                data = resp.read()
            zf = zipfile.ZipFile(io.BytesIO(data))
            tmpdir = tempfile.mkdtemp(prefix="tpmb2_update_")
            zf.extractall(tmpdir)
            top = next((name for name in zf.namelist() if name.endswith('/')), None)
            base = os.path.join(tmpdir, top) if top else tmpdir
            
            whitelist = [
                "main.py", "requirements.txt", ".gitignore",
                os.path.join("bot"), os.path.join("utils"), os.path.join("gui")
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
            messagebox.showinfo("Update", f"Update applied successfully. Files updated: {copied}\nPlease restart the application.")
        except Exception as e:
            self.root.config(cursor="")
            messagebox.showerror("Update failed", f"Cannot update: {e}")
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

if __name__ == "__main__":
    try:
        app = TPMB2GUI()
        app.run()
    except Exception as e:
        messagebox.showerror("Critical Error", f"Application error: {e}")
