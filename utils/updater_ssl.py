import ssl
from urllib.request import urlopen, Request
import tempfile, zipfile, io, os
import certifi
from tkinter import messagebox

# helper function snippet for updater

def download_github_zip_with_ssl_fallback(url: str, headers: dict) -> bytes:
    try:
        ctx = ssl.create_default_context(cafile=certifi.where())
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30, context=ctx) as resp:
            return resp.read()
    except Exception:
        # fallback unverified
        unverified = ssl.create_default_context()
        unverified.check_hostname = False
        unverified.verify_mode = ssl.CERT_NONE
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30, context=unverified) as resp:
            return resp.read()
