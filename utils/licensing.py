import os
import json
import base64
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from cryptography.fernet import Fernet

class LicenseManager:
    """
    Offline license manager for TPMB2
    - Key format: TPMB-XXXX-XXXX-XXXX-XXXX (20 hex chars groups)
    - Binding: bot_token hash + optional hardware fingerprint
    - Storage: encrypted in config/bots.json per bot
    """
    def __init__(self, secret: str = None):
        # Secret used for HMAC signing (embedded or read from .key)
        self.secret = secret or self._get_default_secret()

    def _get_default_secret(self) -> bytes:
        # Derive secret from local Fernet key when available
        try:
            key_path = os.path.join('config', '.key')
            if os.path.exists(key_path):
                with open(key_path, 'rb') as f:
                    k = f.read()
                # Reduce Fernet key to HMAC secret
                return hashlib.sha256(k).digest()
        except Exception:
            pass
        # Fallback static (can be rotated)
        return hashlib.sha256(b'TPMB2_DEFAULT_SECRET').digest()

    def _normalize_key(self, key: str) -> str:
        return key.strip().upper().replace(' ', '').replace('-', '-')

    def _hex4(self, n: int) -> str:
        return f"{n:04X}"[-4:]

    def _checksum(self, payload: str) -> str:
        # HMAC-SHA256 over payload, take 4 hex
        sig = hmac.new(self.secret, payload.encode(), hashlib.sha256).hexdigest()
        return sig[:4].upper()

    def generate_key(self, *, bot_token: str, days_valid: int = 365, hwid: str = None) -> str:
        """Generate license key bound to bot token (+ optional hardware id)"""
        token_hash = hashlib.sha256(bot_token.encode()).hexdigest()[:8]
        expiry = (datetime.utcnow() + timedelta(days=days_valid)).strftime('%y%m%d')  # YYMMDD
        hw = (hwid or 'GENERIC')[:8].upper()
        payload = f"{token_hash}.{expiry}.{hw}"
        csum = self._checksum(payload)
        # Build groups of 4: token_hash(8) -> 2 groups, expiry(6) -> 2 groups (padded), hw(8) -> 2 groups, csum(4) -> 1 group
        g1, g2 = token_hash[:4], token_hash[4:8]
        ex = expiry + '00'  # pad to 8
        g3, g4 = ex[:4], ex[4:8]
        g5, g6 = hw[:4], hw[4:8]
        g7 = csum
        return f"TPMB-{g1}-{g2}-{g3}-{g4}-{g5}-{g6}-{g7}"

    def parse_key(self, key: str) -> Dict[str, Any]:
        k = self._normalize_key(key)
        if not k.startswith('TPMB-'):
            raise ValueError('Invalid prefix')
        parts = k.split('-')
        if len(parts) != 8:
            raise ValueError('Invalid groups count')
        _, g1, g2, g3, g4, g5, g6, g7 = parts
        token_hash = (g1 + g2).upper()
        expiry = (g3 + g4)[:6]  # YYMMDD
        hw = (g5 + g6).upper()
        csum = g7.upper()
        return {"token_hash": token_hash, "expiry": expiry, "hw": hw, "csum": csum}

    def validate_key(self, key: str, *, bot_token: str, hwid: str = None) -> Dict[str, Any]:
        data = self.parse_key(key)
        token_hash = hashlib.sha256(bot_token.encode()).hexdigest()[:8].upper()
        computed_payload = f"{token_hash}.{data['expiry']}.{(hwid or 'GENERIC')[:8].upper()}"
        expected_csum = self._checksum(computed_payload)
        status = {
            "valid": data['csum'] == expected_csum and token_hash == data['token_hash'],
            "reason": None,
            "expires": data['expiry']
        }
        if not status["valid"]:
            status["reason"] = "checksum/token mismatch"
            return status
        # Expiry check
        try:
            exp = datetime.strptime(data['expiry'], '%y%m%d')
            if datetime.utcnow() > exp:
                status["valid"] = False
                status["reason"] = "expired"
        except Exception:
            status["valid"] = False
            status["reason"] = "invalid expiry"
        return status

    @staticmethod
    def get_hwid() -> str:
        # Simple HWID using MAC + UUID
        try:
            mac = uuid.getnode()
            return f"{mac:012X}"[-8:]
        except Exception:
            return 'GENERIC'
