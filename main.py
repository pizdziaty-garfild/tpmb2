#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TPMB2 - Enhanced Telegram Periodic Message Bot v2.0
Main GUI application for bot management
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import asyncio
from datetime import datetime

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def check_requirements():
    """Check if all required modules are available"""
    required = [('telegram', 'python-telegram-bot'), ('cryptography', 'cryptography'), ('requests', 'requests'), ('certifi', 'certifi'), ('ntplib', 'ntplib')]
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
        self.root.geometry("900x650")
        self.root.minsize(700, 500)
        
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
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        
        bot_menu = tk.Menu(menubar, tearoff=0)
        bot_menu.add_command(label="Start Bot", command=self._start_bot)
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
        
        self.stop_btn = ttk.Button(ctrl_frame, text="Stop Bot", command=self._stop_bot, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=5)
        
        ttk.Label(ctrl_frame, text="Interval (min):").grid(row=0, column=2, padx=(20,5))
        interval_entry = ttk.Entry(ctrl_frame, textvariable=self.interval_var, width=5)
        interval_entry.grid(row=0, column=3)
        interval_entry.bind('<Return>', self._update_interval)
        ttk.Button(ctrl_frame, text="Apply", command=self._update_interval).grid(row=0, column=4, padx=(5,0))
        
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
        ttk.Button(parent, text="Save Token", command=self._save_token).grid(row=0, column=2)
        
        # Message
        ttk.Label(parent, text="Message:").grid(row=1, column=0, sticky=(tk.W,tk.N), pady=(10,2))
        self.msg_text = scrolledtext.ScrolledText(parent, width=60, height=8)
        self.msg_text.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=10, pady=(10,5))
        self.msg_text.insert('1.0', self.config.get_message_text())
        
        ttk.Button(parent, text="Save Message", command=self._save_message).grid(row=2, column=1, sticky=tk.W, padx=10)
    
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
        parent.rowconfigure(1, weight=1)
        
        # Controls
        ctrl_frame = ttk.Frame(parent)
        ctrl_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0,10))
        
        ttk.Label(ctrl_frame, text="Group ID:").grid(row=0, column=0)
        self.group_var = tk.StringVar()
        ttk.Entry(ctrl_frame, textvariable=self.group_var, width=20).grid(row=0, column=1, padx=10)
        ttk.Button(ctrl_frame, text="Add", command=self._add_group).grid(row=0, column=2)
        ttk.Button(ctrl_frame, text="Remove Selected", command=self._remove_group).grid(row=0, column=3, padx=(10,0))
        
        # Groups list
        self.groups_list = tk.Listbox(parent)
        self.groups_list.grid(row=1, column=0, sticky=(tk.W,tk.E,tk.N,tk.S))
        self._refresh_groups()
    
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
            self.stop_btn.config(state=tk.NORMAL)
            self.status_var.set("Starting...")
            messagebox.showinfo("Started", "Bot started in background. Use /start command in Telegram to begin messaging.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start bot: {e}")
    
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
    
    def _save_message(self):
        msg = self.msg_text.get('1.0', tk.END).strip()
        if not msg:
            messagebox.showerror("Error", "Message cannot be empty!")
            return
        self.config.set_message_text(msg)
        messagebox.showinfo("Success", "Message saved!")
    
    def _update_interval(self, event=None):
        try:
            interval = int(self.interval_var.get())
            if interval < 1:
                raise ValueError("Interval must be > 0")
            self.config.set_interval_minutes(interval)
            messagebox.showinfo("Success", f"Interval set to {interval} minutes")
        except ValueError:
            messagebox.showerror("Error", "Enter valid number of minutes!")
            self.interval_var.set(str(self.config.get_interval_minutes()))
    
    def _add_group(self):
        try:
            gid = int(self.group_var.get())
            self.config.add_group(gid)
            self.group_var.set("")
            self._refresh_groups()
            self._update_status()
        except ValueError:
            messagebox.showerror("Error", "Group ID must be a number!")
    
    def _remove_group(self):
        sel = self.groups_list.curselection()
        if not sel:
            return
        item = self.groups_list.get(sel[0])
        gid = int(item.split()[0])
        self.config.remove_group(gid)
        self._refresh_groups()
        self._update_status()
    
    def _refresh_groups(self):
        self.groups_list.delete(0, tk.END)
        for gid in self.config.get_groups():
            self.groups_list.insert(tk.END, f"{gid} - Telegram Group")
    
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
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

if __name__ == "__main__":
    try:
        app = TPMB2GUI()
        app.run()
    except Exception as e:
        messagebox.showerror("Critical Error", f"Application error: {e}")
