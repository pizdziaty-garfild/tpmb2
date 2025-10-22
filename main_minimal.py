#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TPMB2 - Minimal Windows Look (Segoe UI) with per-bot proxy and update button
"""

import sys, os, asyncio, traceback, ssl, tempfile, zipfile, io
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from urllib.request import urlopen, Request
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from utils.scrollable import ScrollableFrame
from utils.logger import setup_logger
from utils.config import Config
from utils.bots_registry import BotRegistry
from utils.licensing import LicenseManager

class App:
    def __init__(self):
        self.cfg = Config()
        self.registry = BotRegistry()
        self.licenser = LicenseManager()
        self.logger = setup_logger()
        
        self.root = tk.Tk()
        self.root.title("TPMB2")
        self.root.geometry("1000x720")
        self.root.minsize(880, 640)
        
        self._styles()
        self._ui()
        self._status_update()
        self.root.after(3000, self._tick)

    def _styles(self):
        style = ttk.Style()
        try:
            style.theme_use('vista')
        except:
            pass
        default_font = ('Segoe UI', 10)
        self.root.option_add('*Font', default_font)
        style.configure('TNotebook.Tab', padding=(16,8), font=('Segoe UI', 10, 'bold'))
        style.configure('TLabel', padding=2)
        style.configure('TButton', padding=(10,4))

    def _ui(self):
        # Status bar
        top = ttk.LabelFrame(self.root, text='Status')
        top.pack(fill=tk.X, padx=10, pady=8)
        self.var_status = tk.StringVar(value='Stopped')
        self.var_groups = tk.StringVar(value='0')
        self.var_license = tk.StringVar(value='No License')
        
        ttk.Label(top, text='Status:').grid(row=0, column=0, sticky='w')
        self.lbl_status = ttk.Label(top, textvariable=self.var_status)
        self.lbl_status.grid(row=0, column=1, sticky='w', padx=(6,20))
        ttk.Label(top, text='Groups:').grid(row=0, column=2, sticky='w')
        ttk.Label(top, textvariable=self.var_groups).grid(row=0, column=3, sticky='w', padx=(6,20))
        ttk.Label(top, text='License:').grid(row=0, column=4, sticky='w')
        self.lbl_license = ttk.Label(top, textvariable=self.var_license)
        self.lbl_license.grid(row=0, column=5, sticky='w')
        
        # Control row
        ctrl = ttk.Frame(self.root)
        ctrl.pack(fill=tk.X, padx=10)
        self.btn_start = ttk.Button(ctrl, text='Start', command=self._start)
        self.btn_restart = ttk.Button(ctrl, text='Restart', command=self._restart, state=tk.DISABLED)
        self.btn_stop = ttk.Button(ctrl, text='Stop', command=self._stop, state=tk.DISABLED)
        self.btn_update = ttk.Button(ctrl, text='Update', command=self._update_github)
        for i, b in enumerate([self.btn_start, self.btn_restart, self.btn_stop, self.btn_update]):
            b.grid(row=0, column=i, padx=(0 if i==0 else 6,0), pady=6)
        
        # Notebook
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6,10))
        
        # Configuration
        tab_cfg = ttk.Frame(self.nb)
        self.nb.add(tab_cfg, text='Configuration')
        s_cfg = ScrollableFrame(tab_cfg); s_cfg.pack(fill=tk.BOTH, expand=True)
        self._tab_config(s_cfg.container)
        
        # Bot Management
        tab_bot = ttk.Frame(self.nb)
        self.nb.add(tab_bot, text='Bot Management')
        s_bot = ScrollableFrame(tab_bot); s_bot.pack(fill=tk.BOTH, expand=True)
        self._tab_bot(s_bot.container)
        
        # Logs
        tab_logs = ttk.Frame(self.nb)
        self.nb.add(tab_logs, text='Logs')
        self._tab_logs(tab_logs)
        
        # Groups
        tab_groups = ttk.Frame(self.nb)
        self.nb.add(tab_groups, text='Groups')
        s_grp = ScrollableFrame(tab_groups); s_grp.pack(fill=tk.BOTH, expand=True)
        self._tab_groups(s_grp.container)

    # Tabs
    def _tab_config(self, parent):
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text='Bot Token:').grid(row=0, column=0, sticky='w', pady=4)
        self.var_token = tk.StringVar()
        ttk.Entry(parent, textvariable=self.var_token, show='*', width=48).grid(row=0, column=1, sticky='ew', padx=8)
        btns = ttk.Frame(parent); btns.grid(row=0, column=2, padx=6)
        ttk.Button(btns, text='Save', command=self._save_token).pack(side=tk.LEFT)
        ttk.Button(btns, text='Test', command=self._test_connection).pack(side=tk.LEFT, padx=6)
        
        # Templates
        frame_t = ttk.LabelFrame(parent, text='Message Templates')
        frame_t.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(10,0))
        frame_t.columnconfigure(1, weight=1)
        ttk.Label(frame_t, text='Active:').grid(row=0, column=0, sticky='w')
        self.var_tpl = tk.StringVar(value=self.cfg.get_active_template_key())
        self.cb_tpl = ttk.Combobox(frame_t, textvariable=self.var_tpl, state='readonly')
        self.cb_tpl['values'] = self.cfg.list_templates()
        self.cb_tpl.grid(row=0, column=1, sticky='ew', padx=8)
        ttk.Button(frame_t, text='Set', command=self._set_tpl).grid(row=0, column=2)
        ttk.Button(frame_t, text='New', command=self._new_tpl).grid(row=0, column=3, padx=6)
        ttk.Button(frame_t, text='Delete', command=self._del_tpl).grid(row=0, column=4)
        
        ttk.Label(parent, text='Message (active template):').grid(row=2, column=0, sticky='nw', pady=(10,2))
        self.txt_msg = scrolledtext.ScrolledText(parent, height=6)
        self.txt_msg.grid(row=2, column=1, columnspan=2, sticky='ew', padx=8)
        self.txt_msg.insert('1.0', self.cfg.get_message_text())
        ttk.Button(parent, text='Save Message', command=self._save_msg).grid(row=3, column=1, sticky='w', padx=8, pady=6)

    def _tab_bot(self, parent):
        parent.columnconfigure(1, weight=1)
        # Active bot
        frame_a = ttk.LabelFrame(parent, text='Active Bot')
        frame_a.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0,8))
        frame_a.columnconfigure(1, weight=1)
        ttk.Label(frame_a, text='Active:').grid(row=0, column=0, sticky='w', pady=4)
        self.var_active = tk.StringVar()
        self.cb_bot = ttk.Combobox(frame_a, textvariable=self.var_active, state='readonly', width=40)
        self._refresh_bots_combo()
        self.cb_bot.grid(row=0, column=1, sticky='ew', padx=8)
        btns = ttk.Frame(frame_a); btns.grid(row=0, column=2)
        ttk.Button(btns, text='Set Active', command=self._set_active).pack(side=tk.LEFT)
        ttk.Button(btns, text='Add', command=self._add_bot).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='Remove', command=self._remove_bot).pack(side=tk.LEFT)
        
        # License
        frame_l = ttk.LabelFrame(parent, text='License')
        frame_l.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(0,8))
        frame_l.columnconfigure(1, weight=1)
        ttk.Label(frame_l, text='Key:').grid(row=0, column=0, sticky='w', pady=4)
        self.var_key = tk.StringVar()
        ttk.Entry(frame_l, textvariable=self.var_key, width=54).grid(row=0, column=1, sticky='ew', padx=8)
        btnl = ttk.Frame(frame_l); btnl.grid(row=0, column=2)
        ttk.Button(btnl, text='Validate', command=self._validate_key).pack(side=tk.LEFT)
        ttk.Button(btnl, text='Activate', command=self._activate_key).pack(side=tk.LEFT, padx=6)
        ttk.Button(btnl, text='Generate', command=self._generate_key).pack(side=tk.LEFT)
        
        # Per-bot SOCKS5
        frame_p = ttk.LabelFrame(parent, text='SOCKS5 Proxy (Per-Bot)')
        frame_p.grid(row=2, column=0, columnspan=3, sticky='ew')
        ttk.Label(frame_p, text='Enable:').grid(row=0, column=0, sticky='w', pady=4)
        self.var_proxy_enabled = tk.BooleanVar()
        ttk.Checkbutton(frame_p, variable=self.var_proxy_enabled).grid(row=0, column=1, sticky='w')
        ttk.Label(frame_p, text='Host:').grid(row=0, column=2, sticky='e')
        self.var_proxy_host = tk.StringVar(value='127.0.0.1')
        ttk.Entry(frame_p, textvariable=self.var_proxy_host, width=18).grid(row=0, column=3, padx=6)
        ttk.Label(frame_p, text='Port:').grid(row=0, column=4, sticky='e')
        self.var_proxy_port = tk.StringVar(value='1080')
        ttk.Entry(frame_p, textvariable=self.var_proxy_port, width=6).grid(row=0, column=5, padx=6)
        ttk.Label(frame_p, text='User:').grid(row=1, column=2, sticky='e')
        self.var_proxy_user = tk.StringVar()
        ttk.Entry(frame_p, textvariable=self.var_proxy_user, width=18).grid(row=1, column=3, padx=6)
        ttk.Label(frame_p, text='Pass:').grid(row=1, column=4, sticky='e')
        self.var_proxy_pass = tk.StringVar()
        ttk.Entry(frame_p, textvariable=self.var_proxy_pass, show='*', width=18).grid(row=1, column=5, padx=6)
        
        btnp = ttk.Frame(frame_p)
        btnp.grid(row=2, column=0, columnspan=6, pady=6)
        ttk.Button(btnp, text='Save Proxy', command=self._save_bot_proxy).pack(side=tk.LEFT)
        ttk.Button(btnp, text='Test Connection', command=self._test_bot_proxy).pack(side=tk.LEFT, padx=6)
        
        self._load_bot_proxy_into_ui()
        
        # Info box
        frame_i = ttk.LabelFrame(parent, text='Bot Information')
        frame_i.grid(row=3, column=0, columnspan=3, sticky='nsew', pady=(8,0))
        parent.rowconfigure(3, weight=1)
        self.info = scrolledtext.ScrolledText(frame_i, height=10)
        self.info.pack(fill=tk.BOTH, expand=True)
        self._update_bot_info()

    def _tab_logs(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        ctrl = ttk.Frame(parent)
        ctrl.grid(row=0, column=0, sticky='ew', pady=(6,6))
        ttk.Button(ctrl, text='Refresh', command=self._refresh_logs).pack(side=tk.LEFT)
        ttk.Button(ctrl, text='Open Logs Folder', command=self._open_logs_folder).pack(side=tk.LEFT, padx=6)
        self.logs = scrolledtext.ScrolledText(parent)
        self.logs.grid(row=1, column=0, sticky='nsew')
        self._refresh_logs()

    def _tab_groups(self, parent):
        parent.columnconfigure(0, weight=1)
        ctrl = ttk.Frame(parent); ctrl.grid(row=0, column=0, sticky='ew', pady=(0,6))
        ttk.Label(ctrl, text='Group ID:').pack(side=tk.LEFT)
        self.var_gid = tk.StringVar(); ttk.Entry(ctrl, textvariable=self.var_gid, width=18).pack(side=tk.LEFT, padx=6)
        ttk.Label(ctrl, text='Name:').pack(side=tk.LEFT)
        self.var_gname = tk.StringVar(); ttk.Entry(ctrl, textvariable=self.var_gname, width=18).pack(side=tk.LEFT, padx=6)
        ttk.Button(ctrl, text='Add', command=self._add_group).pack(side=tk.LEFT, padx=6)
        
        bulk = ttk.LabelFrame(parent, text="Bulk (ID;Name per line)")
        bulk.grid(row=1, column=0, sticky='ew')
        self.txt_bulk = scrolledtext.ScrolledText(bulk, height=5)
        self.txt_bulk.pack(fill=tk.BOTH, expand=True)
        btns = ttk.Frame(parent); btns.grid(row=2, column=0, sticky='w', pady=6)
        ttk.Button(btns, text='Add Bulk', command=self._add_bulk).pack(side=tk.LEFT)
        ttk.Button(btns, text='Clear', command=lambda: self.txt_bulk.delete('1.0', tk.END)).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='Deduplicate', command=self._dedup).pack(side=tk.LEFT, padx=6)
        
        frame_list = ttk.LabelFrame(parent, text='Groups')
        frame_list.grid(row=3, column=0, sticky='nsew', pady=(6,0))
        parent.rowconfigure(3, weight=1)
        self.list_groups = tk.Listbox(frame_list)
        self.list_groups.pack(fill=tk.BOTH, expand=True)
        self._refresh_groups()

    # Actions
    def _start(self):
        try:
            from bot.core import TelegramBot
            self.bot = TelegramBot()
            self._set_running(True)
            messagebox.showinfo('Started', 'Bot started in background')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _restart(self):
        try:
            if not hasattr(self, 'bot') or not self.bot:
                return
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            loop.run_until_complete(self.bot.restart_messaging())
            loop.close()
            messagebox.showinfo('Restarted', 'Bot restarted successfully')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _stop(self):
        try:
            self._set_running(False)
        except Exception:
            pass

    def _set_running(self, running: bool):
        self.btn_start.config(state=tk.DISABLED if running else tk.NORMAL)
        self.btn_restart.config(state=tk.NORMAL if running else tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL if running else tk.DISABLED)
        self.var_status.set('Running' if running else 'Stopped')

    def _save_token(self):
        tok = self.var_token.get().strip()
        if not tok:
            messagebox.showerror('Error', 'Enter token')
            return
        self.cfg.set_bot_token(tok)
        self.var_token.set('')
        messagebox.showinfo('Saved', 'Token saved')
        self._status_update()

    def _test_connection(self):
        try:
            from bot.security import SecurityManager
            ok = SecurityManager().verify_telegram_api()
            messagebox.showinfo('Connection', 'OK' if ok else 'Failed')
        except Exception as e:
            messagebox.showerror('Connection', str(e))

    def _set_tpl(self):
        self.cfg.set_active_template_key(self.var_tpl.get())
        self.txt_msg.delete('1.0', tk.END)
        self.txt_msg.insert('1.0', self.cfg.get_message_text())

    def _new_tpl(self):
        key = simpledialog.askstring('New Template', 'Key:')
        if key:
            self.cfg.set_template(key, 'New template {timestamp}')
            self.cb_tpl['values'] = self.cfg.list_templates()
            self.var_tpl.set(key)

    def _del_tpl(self):
        key = self.var_tpl.get()
        if key == self.cfg.get_active_template_key():
            messagebox.showerror('Templates', 'Cannot delete active')
            return
        if messagebox.askyesno('Templates', f'Delete template "{key}"?'):
            self.cfg.remove_template(key)
            self.cb_tpl['values'] = self.cfg.list_templates()
            self.var_tpl.set(self.cfg.get_active_template_key())

    def _save_msg(self):
        msg = self.txt_msg.get('1.0', tk.END).strip()
        if not msg:
            messagebox.showerror('Error', 'Message cannot be empty')
            return
        self.cfg.set_message_text(msg)
        messagebox.showinfo('Saved', 'Message saved')

    # Bot management
    def _refresh_bots_combo(self):
        bots = self.registry.list_bots()
        self.cb_bot['values'] = bots if bots else ['(create first bot)']
        act = self.registry.get_active_bot()
        if act and act in bots:
            self.cb_bot.set(act)
        elif bots:
            self.cb_bot.current(0)

    def _set_active(self):
        sel = self.cb_bot.get()
        if sel and self.registry.set_active_bot(sel):
            messagebox.showinfo('Active Bot', f'Active bot set to: {sel}')
            self._load_bot_proxy_into_ui()
            self._update_bot_info()

    def _add_bot(self):
        bid = simpledialog.askstring('Add Bot', 'Bot ID:')
        if not bid:
            return
        name = simpledialog.askstring('Add Bot', 'Display Name:', initialvalue=bid) or bid
        if self.registry.add_bot(bid, name):
            self._refresh_bots_combo()
            messagebox.showinfo('Added', f'Bot "{bid}" added')

    def _remove_bot(self):
        act = self.registry.get_active_bot()
        if not act:
            return
        if messagebox.askyesno('Remove', f'Remove bot "{act}"?'):
            if self.registry.remove_bot(act):
                self._refresh_bots_combo()
                self._update_bot_info()

    # License
    def _validate_key(self):
        key = self.var_key.get().strip()
        tok = self.cfg.get_bot_token()
        if not key or not tok:
            messagebox.showwarning('License', 'Enter key and configure token')
            return
        st = self.licenser.validate_key(key, bot_token=tok, hwid=self.licenser.get_hwid())
        messagebox.showinfo('License', f"Valid: {st.get('valid')}\nReason: {st.get('reason')}")

    def _activate_key(self):
        act = self.registry.get_active_bot()
        if not act:
            return
        res = self.registry.set_license(act, self.var_key.get().strip())
        messagebox.showinfo('License', f"Activated: {res.get('ok')}\nStatus: {res.get('status')}")
        self._status_update(); self._update_bot_info()

    def _generate_key(self):
        tok = self.cfg.get_bot_token()
        if not tok:
            messagebox.showerror('License', 'Configure token first')
            return
        days = simpledialog.askinteger('Generate', 'Validity (days):', initialvalue=365, minvalue=1)
        if not days:
            return
        key = self.licenser.generate_key(bot_token=tok, days_valid=days, hwid=self.licenser.get_hwid())
        self.var_key.set(key); self.root.clipboard_clear(); self.root.clipboard_append(key)
        messagebox.showinfo('License', 'Key generated and copied to clipboard')

    # Per-bot proxy
    def _load_bot_proxy_into_ui(self):
        act = self.registry.get_active_bot()
        if not act:
            return
        px = self.registry.get_bot_proxy_config(act)
        self.var_proxy_enabled.set(px.get('enabled', False))
        self.var_proxy_host.set(px.get('host', '127.0.0.1'))
        self.var_proxy_port.set(str(px.get('port', 1080)))
        self.var_proxy_user.set(px.get('username', ''))
        self.var_proxy_pass.set('')

    def _save_bot_proxy(self):
        act = self.registry.get_active_bot()
        if not act:
            return
        try:
            port = int(self.var_proxy_port.get())
            ok = self.registry.set_bot_proxy_config(act,
                enabled=self.var_proxy_enabled.get(),
                host=self.var_proxy_host.get().strip() or '127.0.0.1',
                port=port,
                username=self.var_proxy_user.get().strip(),
                password=self.var_proxy_pass.get())
            if ok:
                self.var_proxy_pass.set('')
                messagebox.showinfo('Proxy', 'Saved')
            else:
                messagebox.showerror('Proxy', 'Save failed')
        except ValueError:
            messagebox.showerror('Proxy', 'Invalid port')

    def _test_bot_proxy(self):
        act = self.registry.get_active_bot()
        if not act:
            return
        px = self.registry.get_bot_proxy_config(act)
        messagebox.showinfo('Proxy', f"Enabled: {px.get('enabled')}\nHost: {px.get('host')}\nPort: {px.get('port')}\nUser: {px.get('username') or '(none)'}")

    # Groups
    def _add_group(self):
        try:
            gid = int(self.var_gid.get().strip())
            name = self.var_gname.get().strip() or None
            if self.cfg.add_group(gid, name):
                self.var_gid.set(''); self.var_gname.set('')
                self._refresh_groups(); self._status_update()
        except Exception as e:
            messagebox.showerror('Groups', str(e))

    def _add_bulk(self):
        lines = [ln.strip() for ln in self.txt_bulk.get('1.0', tk.END).splitlines() if ln.strip()]
        added, skipped = 0, 0
        for ln in lines:
            try:
                if ';' in ln:
                    idp, name = ln.split(';', 1)
                    if self.cfg.add_group(int(idp.strip()), name.strip() or None):
                        added += 1
                    else:
                        skipped += 1
                else:
                    if self.cfg.add_group(int(ln)):
                        added += 1
                    else:
                        skipped += 1
            except:
                skipped += 1
        self._refresh_groups(); self._status_update()
        messagebox.showinfo('Bulk', f'Added: {added}\nSkipped: {skipped}')

    def _dedup(self):
        removed = self.cfg.deduplicate_groups()
        if removed:
            self._refresh_groups(); self._status_update()
        messagebox.showinfo('Deduplicate', f'Removed: {removed}')

    def _refresh_groups(self):
        self.list_groups.delete(0, tk.END)
        for g in self.cfg.get_groups_objects():
            self.list_groups.insert(tk.END, f"{g['id']} — {g.get('name') or '(no name)'}")

    # Logs
    def _refresh_logs(self):
        path = os.path.join('logs', 'bot.log')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-200:]
            content = ''.join(lines)
        else:
            content = 'No logs yet.'
        self.logs.delete('1.0', tk.END)
        self.logs.insert('1.0', content)
        self.logs.see(tk.END)

    def _open_logs_folder(self):
        os.startfile(os.path.join(current_dir, 'logs'))

    # Update button
    def _update_github(self):
        try:
            if not messagebox.askyesno('Update', 'Download and apply latest update?'):
                return
            url = 'https://codeload.github.com/pizdziaty-garfild/tpmb2/zip/refs/heads/main'
            headers = {'User-Agent': 'TPMB2-Updater'}
            try:
                import certifi
                cafile = certifi.where()
                ctx = ssl.create_default_context(cafile=cafile)
                data = urlopen(Request(url, headers=headers), timeout=30, context=ctx).read()
            except Exception:
                ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
                data = urlopen(Request(url, headers=headers), timeout=30, context=ctx).read()
            zf = zipfile.ZipFile(io.BytesIO(data))
            tmp = tempfile.mkdtemp(prefix='tpmb2_update_')
            zf.extractall(tmp)
            top = next((n for n in zf.namelist() if n.endswith('/')), None)
            base = os.path.join(tmp, top) if top else tmp
            whitelist = ['main.py', 'README.md', 'requirements.txt', 'bot', 'utils']
            preserved = ['config', 'logs']
            copied=0
            for root, dirs, files in os.walk(base):
                rel = os.path.relpath(root, base)
                if rel == '.': rel = ''
                if any(rel.startswith(p) for p in preserved if rel):
                    continue
                if rel and not any(rel.split(os.sep)[0] == w for w in whitelist):
                    continue
                target_root = os.path.join(current_dir, rel) if rel else current_dir
                os.makedirs(target_root, exist_ok=True)
                for f in files:
                    src = os.path.join(root, f); dst = os.path.join(target_root, f)
                    if any(dst.startswith(os.path.join(current_dir, p)) for p in preserved):
                        continue
                    with open(src, 'rb') as rf, open(dst, 'wb') as wf:
                        wf.write(rf.read()); copied += 1
            messagebox.showinfo('Update', f'Update applied. Files: {copied}\nPlease restart the app.')
        except Exception as e:
            messagebox.showerror('Update', str(e))

    # Status
    def _status_update(self):
        self.var_groups.set(str(len(self.cfg.get_groups())))
        act = self.registry.get_active_bot()
        if act:
            bot = self.registry.get_bot(act)
            key = bot.get('license_key', '')
            token = self.cfg.get_bot_token()
            if key and token:
                st = self.licenser.validate_key(key, bot_token=token, hwid=self.licenser.get_hwid())
                if st.get('valid'):
                    self.var_license.set('Active')
                    self.lbl_license.config(foreground='green')
                else:
                    self.var_license.set('Invalid')
                    self.lbl_license.config(foreground='red')
            else:
                self.var_license.set('No License')
                self.lbl_license.config(foreground='red')
        else:
            self.var_license.set('No Bot')
            self.lbl_license.config(foreground='red')

    def _update_bot_info(self):
        act = self.registry.get_active_bot()
        if not act:
            self.info.delete('1.0', tk.END)
            self.info.insert('1.0', 'No active bot selected')
            return
        bot = self.registry.get_bot(act)
        px = self.registry.get_bot_proxy_config(act)
        txt = (
            f"Bot ID: {act}\n"
            f"Name: {bot.get('name')}\n"
            f"License: {bot.get('license_status')}\n"
            f"Proxy: {'Enabled' if px.get('enabled') else 'Disabled'}\n"
            f"Host: {px.get('host')}  Port: {px.get('port')}  User: {px.get('username') or '(none)'}\n"
        )
        self.info.delete('1.0', tk.END)
        self.info.insert('1.0', txt)

    def _tick(self):
        self._status_update()
        self.root.after(3000, self._tick)

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    App().run()
