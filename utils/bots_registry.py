import json
import os
from typing import Dict, Any, List
from .config import Config
from .licensing import LicenseManager

class BotRegistry:
    """
    Manage multiple bots and their licenses.
    Stores data in config/bots.json.
    """
    def __init__(self, config_dir: str = 'config'):
        self.config_dir = config_dir
        self.registry_file = os.path.join(config_dir, 'bots.json')
        os.makedirs(config_dir, exist_ok=True)
        self._load()
        self.licenser = LicenseManager()

    def _default(self) -> Dict[str, Any]:
        return {
            "active_bot": None,
            "bots": {}
        }

    def _load(self):
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    self.registry = json.load(f)
            except Exception:
                self.registry = self._default()
        else:
            self.registry = self._default()
            self._save()

    def _save(self):
        with open(self.registry_file, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)

    # CRUD operations
    def list_bots(self) -> List[str]:
        return list(self.registry.get('bots', {}).keys())

    def get_active_bot(self) -> str:
        return self.registry.get('active_bot')

    def set_active_bot(self, bot_id: str) -> bool:
        if bot_id in self.registry.get('bots', {}):
            self.registry['active_bot'] = bot_id
            self._save()
            return True
        return False

    def add_bot(self, bot_id: str, name: str, token_encrypted: str = "") -> bool:
        if bot_id in self.registry.get('bots', {}):
            return False
        self.registry['bots'][bot_id] = {
            "name": name,
            "token_encrypted": token_encrypted,
            "license_key": None,
            "license_status": "inactive",
            "created_date": None
        }
        if not self.registry.get('active_bot'):
            self.registry['active_bot'] = bot_id
        self._save()
        return True

    def remove_bot(self, bot_id: str) -> bool:
        if bot_id in self.registry.get('bots', {}):
            del self.registry['bots'][bot_id]
            if self.registry.get('active_bot') == bot_id:
                self.registry['active_bot'] = next(iter(self.registry['bots']), None)
            self._save()
            return True
        return False

    def set_license(self, bot_id: str, license_key: str) -> Dict[str, Any]:
        bot = self.registry['bots'].get(bot_id)
        if not bot:
            return {"ok": False, "reason": "bot not found"}
        # Validate license
        cfg = Config()  # to decrypt token
        token = cfg.get_bot_token()  # current token in use (for active bot)
        status = self.licenser.validate_key(license_key, bot_token=token, hwid=self.licenser.get_hwid())
        bot['license_key'] = license_key
        bot['license_status'] = 'active' if status['valid'] else f"invalid: {status.get('reason')}"
        self._save()
        return {"ok": status['valid'], "status": status}

    def get_bot(self, bot_id: str) -> Dict[str, Any]:
        return self.registry['bots'].get(bot_id, {})
