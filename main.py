#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TPMB2 - Windows XP Blue UI (Tahoma 9, XP-style tabs/buttons/panels)
This replaces only the presentation layer; logic remains intact.
"""

import sys, os, asyncio, ssl, tempfile, zipfile, io
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from urllib.request import urlopen, Request

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from utils.scrollable import ScrollableFrame
from utils.logger import setup_logger
from utils.config import Config
from utils.bots_registry import BotRegistry
from utils.licensing import LicenseManager

# XP theme
try:
    from gui.theme_xp import apply_xp_theme, XPColors
    from gui.widgets_xp import XPToolbar, XPStatusBar
except Exception:
    from theme_xp import apply_xp_theme, XPColors
    from widgets_xp import XPToolbar, XPStatusBar


class TPMB2:
    def __init__(self):
        self.cfg = Config()
        self.registry = BotRegistry()
        self.licenser = LicenseManager()
        self.logger = setup_logger()
        
        self.root = tk.Tk()
        self.root.title('TPMB2')
        self.root.geometry('980x720')
        self.root.minsize(880, 640)
        
        # Apply XP theme
        self.theme = apply_xp_theme(self.root)
        self.root.option_add('*Font', ('Tahoma', 9))
        
        self._build()
        self._refresh_status()
        self.root.after(3000, self._tick)

    def _build(self):
        # Toolbar (XP style)
        self.toolbar = XPToolbar(self.root)
        self.toolbar.pack(fill=tk.X)
        
        self.btn_start = self.toolbar.add_button('start', 'Start', self._start)
        self.btn_restart = self.toolbar.add_button('restart', 'Restart', self._restart)
        self.btn_stop = self.toolbar.add_button('stop', 'Stop', self._stop)
        self.toolbar.add_separator()
        self.btn_update = self.toolbar.add_button('update', 'Update', self._update)
        
        # Top status strip (labels on the right)
        top = ttk.Frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=(6,6))
        
        self.var_status = tk.StringVar(value='Stopped')
        self.var_groups = tk.StringVar(value='0')
        self.var_license = tk.StringVar(value='No License')
        
        status_box = ttk.Frame(top)
        status_box.pack(side=tk.RIGHT)
        ttk.Label(status_box, text='Status:').pack(side=tk.LEFT)
        self.lbl_status = ttk.Label(status_box, textvariable=self.var_status, foreground='red')
        self.lbl_status.pack(side=tk.LEFT, padx=(4,12))
        ttk.Label(status_box, text='Groups:').pack(side=tk.LEFT)
        ttk.Label(status_box, textvariable=self.var_groups).pack(side=tk.LEFT, padx=(4,12))
        ttk.Label(status_box, text='License:').pack(side=tk.LEFT)
        self.lbl_license = ttk.Label(status_box, textvariable=self.var_license)
        self.lbl_license.pack(side=tk.LEFT, padx=(4,0))

        # Notebook
        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        
        # Tabs
        t_cfg = ttk.Frame(nb); nb.add(t_cfg, text='Configuration')
        t_bot = ttk.Frame(nb); nb.add(t_bot, text='Bot Management')
        t_logs = ttk.Frame(nb); nb.add(t_logs, text='Logs')
        t_grp = ttk.Frame(nb); nb.add(t_grp, text='Groups')
        t_st = ttk.Frame(nb); nb.add(t_st, text='Status')
        
        s_cfg = ScrollableFrame(t_cfg); s_cfg.pack(fill=tk.BOTH, expand=True)
        self._tab_config(s_cfg.container)
        s_bot = ScrollableFrame(t_bot); s_bot.pack(fill=tk.BOTH, expand=True)
        self._tab_bot(s_bot.container)
        self._tab_logs(t_logs)
        s_grp = ScrollableFrame(t_grp); s_grp.pack(fill=tk.BOTH, expand=True)
        self._tab_groups(s_grp.container)
        self._tab_status(t_st)
        
        # Status bar
        self.statusbar = XPStatusBar(self.root)
        self.statusbar.pack(fill=tk.X)
        self.statusbar.add_field('hint', 'Ready')

    # Tabs (reuse existing logic, only layout tweaks)
    def _tab_config(self, p):
        p.columnconfigure(1, weight=1)
        
        lf_top = ttk.LabelFrame(p, text='Bot & License'); lf_top.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(6,6))
        lf_top.columnconfigure(1, weight=1)
        ttk.Label(lf_top, text='Bot Token:').grid(row=0, column=0, sticky='w', pady=4)
        self.var_token = tk.StringVar()
        ttk.Entry(lf_top, textvariable=self.var_token, show='*', width=50).grid(row=0, column=1, sticky='ew', padx=8)
        ttk.Button(lf_top, text='Save', command=self._save_token, style='XP.TButton').grid(row=0, column=2)
        ttk.Button(lf_top, text='Test', command=self._test_conn).grid(row=0, column=3, padx=6)
        
        lf_tpl = ttk.LabelFrame(p, text='Message Templates'); lf_tpl.grid(row=1, column=0, columnspan=3, sticky='ew')
        lf_tpl.columnconfigure(1, weight=1)
        ttk.Label(lf_tpl, text='Active:').grid(row=0, column=0, sticky='w', pady=4)
        self.var_tpl = tk.StringVar(value=self.cfg.get_active_template_key())
        self.cb_tpl = ttk.Combobox(lf_tpl, textvariable=self.var_tpl, state='readonly')
        self.cb_tpl['values'] = self.cfg.list_templates(); self.cb_tpl.grid(row=0, column=1, sticky='ew', padx=8)
        ttk.Button(lf_tpl, text='Set', command=self._tpl_set).grid(row=0, column=2)
        ttk.Button(lf_tpl, text='New', command=self._tpl_new).grid(row=0, column=3, padx=6)
        ttk.Button(lf_tpl, text='Delete', command=self._tpl_del).grid(row=0, column=4)
        
        ttk.Label(p, text='Message (active template):').grid(row=2, column=0, sticky='nw', pady=(8,2))
        self.txt_msg = scrolledtext.ScrolledText(p, height=6)
        self.txt_msg.grid(row=2, column=1, columnspan=2, sticky='ew', padx=8)
        self.txt_msg.insert('1.0', self.cfg.get_message_text())
        ttk.Button(p, text='Save Message', command=self._msg_save, style='XP.TButton').grid(row=3, column=1, sticky='w', padx=8, pady=6)

    def _tab_bot(self, p):
        p.columnconfigure(1, weight=1)
        lf_a = ttk.LabelFrame(p, text='Active Bot'); lf_a.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0,6))
        lf_a.columnconfigure(1, weight=1)
        ttk.Label(lf_a, text='Active:').grid(row=0, column=0, sticky='w', pady=4)
        self.var_active = tk.StringVar()
        self.cb_bot = ttk.Combobox(lf_a, textvariable=self.var_active, state='readonly', width=40)
        self._bots_reload(); self.cb_bot.grid(row=0, column=1, sticky='ew', padx=8)
        ab = ttk.Frame(lf_a); ab.grid(row=0, column=2)
        ttk.Button(ab, text='Set Active', command=self._bot_set_active, style='XP.TButton').pack(side=tk.LEFT)
        ttk.Button(ab, text='Add', command=self._bot_add).pack(side=tk.LEFT, padx=6)
        ttk.Button(ab, text='Remove', command=self._bot_remove).pack(side=tk.LEFT)
        
        lf_l = ttk.LabelFrame(p, text='License'); lf_l.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(0,6))
        lf_l.columnconfigure(1, weight=1)
        ttk.Label(lf_l, text='Key:').grid(row=0, column=0, sticky='w', pady=4)
        self.var_key = tk.StringVar(); ttk.Entry(lf_l, textvariable=self.var_key, width=54).grid(row=0, column=1, sticky='ew', padx=8)
        lb = ttk.Frame(lf_l); lb.grid(row=0, column=2)
        ttk.Button(lb, text='Validate', command=self._lic_validate).pack(side=tk.LEFT)
        ttk.Button(lb, text='Activate', command=self._lic_activate).pack(side=tk.LEFT, padx=6)
        ttk.Button(lb, text='Generate', command=self._lic_generate).pack(side=tk.LEFT)
        
        lf_p = ttk.LabelFrame(p, text='SOCKS5 Proxy (Per-Bot)'); lf_p.grid(row=2, column=0, columnspan=3, sticky='ew')
        ttk.Label(lf_p, text='Enable:').grid(row=0, column=0, sticky='w', pady=4)
        self.var_p_en = tk.BooleanVar(); ttk.Checkbutton(lf_p, variable=self.var_p_en).grid(row=0, column=1, sticky='w')
        ttk.Label(lf_p, text='Host:').grid(row=0, column=2, sticky='e')
        self.var_p_host = tk.StringVar(value='127.0.0.1'); ttk.Entry(lf_p, textvariable=self.var_p_host, width=18).grid(row=0, column=3, padx=6)
        ttk.Label(lf_p, text='Port:').grid(row=0, column=4, sticky='e')
        self.var_p_port = tk.StringVar(value='1080'); ttk.Entry(lf_p, textvariable=self.var_p_port, width=6).grid(row=0, column=5, padx=6)
        ttk.Label(lf_p, text='User:').grid(row=1, column=2, sticky='e'); self.var_p_user = tk.StringVar(); ttk.Entry(lf_p, textvariable=self.var_p_user, width=18).grid(row=1, column=3, padx=6)
        ttk.Label(lf_p, text='Pass:').grid(row=1, column=4, sticky='e'); self.var_p_pass = tk.StringVar(); ttk.Entry(lf_p, textvariable=self.var_p_pass, show='*', width=18).grid(row=1, column=5, padx=6)
        pb = ttk.Frame(lf_p); pb.grid(row=2, column=0, columnspan=6, pady=6)
        ttk.Button(pb, text='Save Proxy', command=self._proxy_save, style='XP.TButton').pack(side=tk.LEFT)
        ttk.Button(pb, text='Test Connection', command=self._proxy_test).pack(side=tk.LEFT, padx=6)
        self._proxy_load()
        
        lf_i = ttk.LabelFrame(p, text='Bot Information'); lf_i.grid(row=3, column=0, columnspan=3, sticky='nsew', pady=(6,0))
        p.rowconfigure(3, weight=1)
        self.txt_info = scrolledtext.ScrolledText(lf_i, height=10)
        self.txt_info.pack(fill=tk.BOTH, expand=True)
        self._bot_info_update()

    def _tab_logs(self, p):
        p.columnconfigure(0, weight=1); p.rowconfigure(1, weight=1)
        ctrl = ttk.Frame(p); ctrl.grid(row=0, column=0, sticky='ew', pady=(6,6))
        ttk.Button(ctrl, text='Refresh', command=self._logs_refresh, style='XP.TButton').pack(side=tk.LEFT)
        ttk.Button(ctrl, text='Open Logs Folder', command=self._logs_open).pack(side=tk.LEFT, padx=6)
        self.txt_logs = scrolledtext.ScrolledText(p)
        self.txt_logs.grid(row=1, column=0, sticky='nsew')
        self._logs_refresh()

    def _tab_groups(self, p):
        p.columnconfigure(0, weight=1)
        ctrl = ttk.Frame(p); ctrl.grid(row=0, column=0, sticky='ew', pady=(0,6))
        ttk.Label(ctrl, text='Group ID:').pack(side=tk.LEFT)
        self.var_gid = tk.StringVar(); ttk.Entry(ctrl, textvariable=self.var_gid, width=18).pack(side=tk.LEFT, padx=6)
        ttk.Label(ctrl, text='Name:').pack(side=tk.LEFT)
        self.var_gn = tk.StringVar(); ttk.Entry(ctrl, textvariable=self.var_gn, width=18).pack(side=tk.LEFT, padx=6)
        ttk.Button(ctrl, text='Add', command=self._grp_add, style='XP.TButton').pack(side=tk.LEFT, padx=6)
        
        bulk = ttk.LabelFrame(p, text='Bulk (ID;Name per line)'); bulk.grid(row=1, column=0, sticky='ew')
        self.txt_bulk = scrolledtext.ScrolledText(bulk, height=5); self.txt_bulk.pack(fill=tk.BOTH, expand=True)
        bb = ttk.Frame(p); bb.grid(row=2, column=0, sticky='w', pady=6)
        ttk.Button(bb, text='Add Bulk', command=self._grp_bulk).pack(side=tk.LEFT)
        ttk.Button(bb, text='Clear', command=lambda: self.txt_bulk.delete('1.0', tk.END)).pack(side=tk.LEFT, padx=6)
        ttk.Button(bb, text='Deduplicate', command=self._grp_dedup).pack(side=tk.LEFT, padx=6)
        
        lf = ttk.LabelFrame(p, text='Groups'); lf.grid(row=3, column=0, sticky='nsew', pady=(6,0))
        p.rowconfigure(3, weight=1)
        self.lst_groups = tk.Listbox(lf); self.lst_groups.pack(fill=tk.BOTH, expand=True)
        self._groups_refresh()

    def _tab_status(self, p):
        p.columnconfigure((0,1), weight=1)
        box1 = ttk.LabelFrame(p, text='Runtime'); box1.grid(row=0, column=0, sticky='ew', padx=(0,6), pady=(6,6))
        ttk.Label(box1, text='Running:').grid(row=0, column=0, sticky='w'); self.lbl_run = ttk.Label(box1, text='No', foreground='red'); self.lbl_run.grid(row=0, column=1, sticky='w')
        ttk.Label(box1, text='Uptime:').grid(row=1, column=0, sticky='w'); self.lbl_up = ttk.Label(box1, text='0:00:00'); self.lbl_up.grid(row=1, column=1, sticky='w')
        
        box2 = ttk.LabelFrame(p, text='Stats'); box2.grid(row=0, column=1, sticky='ew', pady=(6,6))
        ttk.Label(box2, text='Messages sent:').grid(row=0, column=0, sticky='w'); self.lbl_sent = ttk.Label(box2, text='0'); self.lbl_sent.grid(row=0, column=1, sticky='w')

    # Buttons and logic reused
    def _start(self):
        from bot.core import TelegramBot
        self.bot = TelegramBot()
        self._set_running(True)
        messagebox.showinfo('Started', 'Bot started in background')

    def _restart(self):
        if not hasattr(self, 'bot') or not self.bot: return
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        loop.run_until_complete(self.bot.restart_messaging()); loop.close()
        messagebox.showinfo('Restarted', 'Bot restarted')

    def _stop(self):
        self._set_running(False)

    def _set_running(self, on):
        self.btn_start.config(state=tk.DISABLED if on else tk.NORMAL)
        self.btn_restart.config(state=tk.NORMAL if on else tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL if on else tk.DISABLED)
        self.var_status.set('Running' if on else 'Stopped')
        self.lbl_status.config(foreground='green' if on else 'red')

    # Config / templates (unchanged)
    def _save_token(self):
        t = self.var_token.get().strip()
        if not t: messagebox.showerror('Token', 'Enter token'); return
        self.cfg.set_bot_token(t); self.var_token.set(''); messagebox.showinfo('Token', 'Saved')
        self._refresh_status()

    def _test_conn(self):
        try:
            from bot.security import SecurityManager
            ok = SecurityManager().verify_telegram_api()
            messagebox.showinfo('Connection', 'OK' if ok else 'Failed')
        except Exception as e:
            messagebox.showerror('Connection', str(e))

    def _tpl_set(self):
        self.cfg.set_active_template_key(self.var_tpl.get())
        self.txt_msg.delete('1.0', tk.END); self.txt_msg.insert('1.0', self.cfg.get_message_text())

    def _tpl_new(self):
        k = simpledialog.askstring('New Template', 'Key:')
        if k:
            self.cfg.set_template(k, 'New template {timestamp}')
            self.cb_tpl['values'] = self.cfg.list_templates(); self.var_tpl.set(k)

    def _tpl_del(self):
        k = self.var_tpl.get()
        if k == self.cfg.get_active_template_key():
            messagebox.showerror('Templates', 'Cannot delete active'); return
        if messagebox.askyesno('Templates', f'Delete "{k}"?'):
            self.cfg.remove_template(k)
            self.cb_tpl['values'] = self.cfg.list_templates(); self.var_tpl.set(self.cfg.get_active_template_key())

    def _msg_save(self):
        m = self.txt_msg.get('1.0', tk.END).strip()
        if not m: messagebox.showerror('Message', 'Cannot be empty'); return
        self.cfg.set_message_text(m); messagebox.showinfo('Message', 'Saved')

    # Bot management (unchanged logic)
    def _bots_reload(self):
        bots = self.registry.list_bots()
        self.cb_bot['values'] = bots if bots else ['(create first bot)']
        a = self.registry.get_active_bot()
        if a and a in bots: self.cb_bot.set(a)
        elif bots: self.cb_bot.current(0)

    def _bot_set_active(self):
        s = self.cb_bot.get()
        if s and self.registry.set_active_bot(s):
            messagebox.showinfo('Active Bot', f'Set to: {s}')
            self._proxy_load(); self._bot_info_update(); self._refresh_status()

    def _bot_add(self):
        i = simpledialog.askstring('Add Bot', 'Bot ID:')
        if not i: return
        n = simpledialog.askstring('Add Bot', 'Display Name:', initialvalue=i) or i
        if self.registry.add_bot(i, n):
            self._bots_reload(); messagebox.showinfo('Bot', 'Added')

    def _bot_remove(self):
        a = self.registry.get_active_bot()
        if not a: return
        if messagebox.askyesno('Remove', f'Remove "{a}"?'):
            if self.registry.remove_bot(a): self._bots_reload(); self._bot_info_update()

    # License
    def _lic_validate(self):
        k = self.var_key.get().strip(); t = self.cfg.get_bot_token()
        if not k or not t: messagebox.showwarning('License', 'Enter key and configure token'); return
        st = self.licenser.validate_key(k, bot_token=t, hwid=self.licenser.get_hwid())
        messagebox.showinfo('License', f"Valid: {st.get('valid')}\nReason: {st.get('reason')}")

    def _lic_activate(self):
        a = self.registry.get_active_bot(); k = self.var_key.get().strip()
        if not a or not k: return
        r = self.registry.set_license(a, k)
        messagebox.showinfo('License', f"Activated: {r.get('ok')}\nStatus: {r.get('status')}")
        self._refresh_status(); self._bot_info_update()

    def _lic_generate(self):
        t = self.cfg.get_bot_token()
        if not t: messagebox.showerror('License', 'Configure token first'); return
        from utils.licensing import LicenseManager
        days = simpledialog.askinteger('Generate', 'Validity (days):', initialvalue=365, minvalue=1)
        if not days: return
        key = LicenseManager().generate_key(bot_token=t, days_valid=days, hwid=LicenseManager().get_hwid())
        self.var_key.set(key); self.root.clipboard_clear(); self.root.clipboard_append(key)
        messagebox.showinfo('License', 'Key generated and copied')

    # Proxy
    def _proxy_load(self):
        a = self.registry.get_active_bot()
        if not a: return
        px = self.registry.get_bot_proxy_config(a)
        self.var_p_en.set(px.get('enabled', False))
        self.var_p_host.set(px.get('host', '127.0.0.1'))
        self.var_p_port.set(str(px.get('port', 1080)))
        self.var_p_user.set(px.get('username', ''))
        self.var_p_pass.set('')

    def _proxy_save(self):
        a = self.registry.get_active_bot()
        if not a: return
        try:
            port = int(self.var_p_port.get())
        except ValueError:
            messagebox.showerror('Proxy', 'Invalid port'); return
        ok = self.registry.set_bot_proxy_config(a,
            enabled=self.var_p_en.get(),
            host=self.var_p_host.get().strip() or '127.0.0.1',
            port=port,
            username=self.var_p_user.get().strip(),
            password=self.var_p_pass.get())
        if ok: self.var_p_pass.set(''); messagebox.showinfo('Proxy', 'Saved')

    def _proxy_test(self):
        a = self.registry.get_active_bot();
        if not a: return
        px = self.registry.get_bot_proxy_config(a)
        messagebox.showinfo('Proxy', f"Enabled: {px.get('enabled')}\nHost: {px.get('host')}\nPort: {px.get('port')}\nUser: {px.get('username') or '(none)'}")

    # Groups
    def _grp_add(self):
        try:
            gid = int(self.var_gid.get().strip()); name = (self.var_gn.get().strip() or None)
            if self.cfg.add_group(gid, name): self.var_gid.set(''); self.var_gn.set(''); self._groups_refresh(); self._refresh_status()
        except Exception as e:
            messagebox.showerror('Groups', str(e))

    def _grp_bulk(self):
        lines = [ln.strip() for ln in self.txt_bulk.get('1.0', tk.END).splitlines() if ln.strip()]
        added, skipped = 0, 0
        for ln in lines:
            try:
                if ';' in ln:
                    idp, name = ln.split(';', 1)
                    if self.cfg.add_group(int(idp.strip()), name.strip() or None): added += 1
                    else: skipped += 1
                else:
                    if self.cfg.add_group(int(ln)): added += 1
                    else: skipped += 1
            except: skipped += 1
        self._groups_refresh(); self._refresh_status()
        messagebox.showinfo('Bulk', f'Added: {added}\nSkipped: {skipped}')

    def _grp_dedup(self):
        r = self.cfg.deduplicate_groups(); self._groups_refresh(); self._refresh_status()
        messagebox.showinfo('Deduplicate', f'Removed: {r}')

    def _groups_refresh(self):
        self.lst_groups.delete(0, tk.END)
        for g in self.cfg.get_groups_objects():
            self.lst_groups.insert(tk.END, f"{g['id']} — {g.get('name') or '(no name)'}")

    # Logs
    def _logs_refresh(self):
        path = os.path.join('logs', 'bot.log')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-200:]
            txt = ''.join(lines)
        else: txt = 'No logs yet.'
        self.txt_logs.delete('1.0', tk.END); self.txt_logs.insert('1.0', txt); self.txt_logs.see(tk.END)

    def _logs_open(self): os.startfile(os.path.join(current_dir, 'logs'))

    # Update
    def _update(self):
        try:
            if not messagebox.askyesno('Update', 'Download and apply latest update?'): return
            url = 'https://codeload.github.com/pizdziaty-garfild/tpmb2/zip/refs/heads/main'
            headers = {'User-Agent': 'TPMB2-Updater'}
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
                data = urlopen(Request(url, headers=headers), timeout=30, context=ctx).read()
            except Exception:
                ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
                data = urlopen(Request(url, headers=headers), timeout=30, context=ctx).read()
            zf = zipfile.ZipFile(io.BytesIO(data))
            tmp = tempfile.mkdtemp(prefix='tpmb2_update_')
            zf.extractall(tmp)
            top = next((n for n in zf.namelist() if n.endswith('/')), None)
            base = os.path.join(tmp, top) if top else tmp
            whitelist = ['main.py','main_minimal.py','README.md','requirements.txt','bot','utils']
            preserved = ['config','logs']
            copied = 0
            for root, dirs, files in os.walk(base):
                rel = os.path.relpath(root, base); rel = '' if rel=='.' else rel
                if any(rel.startswith(p) for p in preserved if rel): continue
                if rel and not any(rel.split(os.sep)[0] == w for w in whitelist): continue
                dst_root = os.path.join(current_dir, rel) if rel else current_dir
                os.makedirs(dst_root, exist_ok=True)
                for f in files:
                    src = os.path.join(root,f); dst = os.path.join(dst_root,f)
                    if any(dst.startswith(os.path.join(current_dir,p)) for p in preserved): continue
                    with open(src,'rb') as rf, open(dst,'wb') as wf: wf.write(rf.read()); copied += 1
            messagebox.showinfo('Update', f'Update applied. Files: {copied}\nPlease restart TPMB2.')
        except Exception as e:
            messagebox.showerror('Update', str(e))

    # Status
    def _refresh_status(self):
        self.var_groups.set(str(len(self.cfg.get_groups())))
        a = self.registry.get_active_bot()
        if a:
            bot = self.registry.get_bot(a)
            key = bot.get('license_key',''); tok = self.cfg.get_bot_token()
            if key and tok:
                st = self.licenser.validate_key(key, bot_token=tok, hwid=self.licenser.get_hwid())
                if st.get('valid'): self.var_license.set('Active'); self.lbl_license.config(foreground='green')
                else: self.var_license.set('Invalid'); self.lbl_license.config(foreground='red')
            else: self.var_license.set('No License'); self.lbl_license.config(foreground='red')
        else:
            self.var_license.set('No Bot'); self.lbl_license.config(foreground='red')

    def _bot_info_update(self):
        a = self.registry.get_active_bot()
        if not a:
            self.txt_info.delete('1.0', tk.END); self.txt_info.insert('1.0', 'No active bot selected'); return
        b = self.registry.get_bot(a); px = self.registry.get_bot_proxy_config(a)
        info = (
            f"Bot ID: {a}\nName: {b.get('name')}\nLicense: {b.get('license_status')}\n"
            f"Proxy: {'Enabled' if px.get('enabled') else 'Disabled'}\nHost: {px.get('host')}  Port: {px.get('port')}  User: {px.get('username') or '(none)'}\n"
        )
        self.txt_info.delete('1.0', tk.END); self.txt_info.insert('1.0', info)

    def _tick(self): self._refresh_status(); self.root.after(3000, self._tick)

    def run(self): self.root.mainloop()

if __name__ == '__main__':
    TPMB2().run()
