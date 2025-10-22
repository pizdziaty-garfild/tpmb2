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
import ssl
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

# ... (rest of file unchanged until _safe_update_from_github)

# NOTE: function bodies above remain as in previous commit
# Only _safe_update_from_github is updated to use certifi and SSL fallback.

    def _safe_update_from_github(self):
        """Updater: fetch latest main.zip from GitHub with robust SSL handling.
        - Try SSL verify with certifi CA bundle first
        - If it fails, offer fallback with verify disabled (user-confirmed)
        - Always preserve config/ and logs/
        """
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
                self.root.config(cursor="watch"); self.root.update()
                with urlopen(req, timeout=30, context=ctx) as resp:
                    data = resp.read()
            except Exception as e_verified:
                # Ask user to fallback without SSL verify
                self.root.config(cursor="")
                if not messagebox.askyesno("Update (SSL)", f"Verified download failed:\n{e_verified}\n\nDo you want to retry WITHOUT certificate verification?\n(Not recommended)"):
                    return
                # Fallback: unverified context
                unverified = ssl.create_default_context()
                unverified.check_hostname = False
                unverified.verify_mode = ssl.CERT_NONE
                req = Request(zip_url, headers=headers)
                self.root.config(cursor="watch"); self.root.update()
                with urlopen(req, timeout=30, context=unverified) as resp:
                    data = resp.read()

            # Extract and copy
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
