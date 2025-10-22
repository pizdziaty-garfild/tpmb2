import json
import os
from typing import List, Dict, Any, Optional
from cryptography.fernet import Fernet
import base64
import logging

class Config:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.settings_file = os.path.join(config_dir, "settings.json")
        self.groups_file = os.path.join(config_dir, "groups.json")
        self.key_file = os.path.join(config_dir, ".key")
        self.logger = logging.getLogger(__name__)
        os.makedirs(config_dir, exist_ok=True)
        self._ensure_encryption_key()
        self._load_or_create_config()

    def _ensure_encryption_key(self):
        if not os.path.exists(self.key_file):
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            try:
                os.chmod(self.key_file, 0o600)
            except Exception:
                pass

    def _cipher(self) -> Fernet:
        with open(self.key_file, 'rb') as f:
            key = f.read()
        return Fernet(key)

    def _load_or_create_config(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
        else:
            self.settings = {
                "bot_token_encrypted": "",
                "admin_ids": [],
                "operator_id": None,
                "message_text": "Automatyczna wiadomosc! Czas: {timestamp}",
                "interval_minutes": 60,
                "auto_start": False,
                "auto_restart": True,
                "owner_info": {
                    "username": "bot_owner",
                    "description": "Administrator bota",
                    "additional_info": "Skontaktuj sie w razie pytan"
                }
            }
            self._save_settings()
        if os.path.exists(self.groups_file):
            with open(self.groups_file, 'r', encoding='utf-8') as f:
                self.groups_data = json.load(f)
        else:
            self.groups_data = {"groups": []}
            self._save_groups()

    def _save_settings(self):
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def _save_groups(self):
        with open(self.groups_file, 'w', encoding='utf-8') as f:
            json.dump(self.groups_data, f, indent=2, ensure_ascii=False)

    def set_bot_token(self, token: str):
        enc = self._cipher().encrypt(token.encode())
        self.settings["bot_token_encrypted"] = base64.b64encode(enc).decode()
        self._save_settings()

    def get_bot_token(self) -> Optional[str]:
        data = self.settings.get("bot_token_encrypted")
        if not data:
            return None
        try:
            enc = base64.b64decode(data)
            return self._cipher().decrypt(enc).decode()
        except Exception:
            return None

    def get_admin_ids(self) -> List[int]:
        return self.settings.get("admin_ids", [])

    def add_admin_id(self, user_id: int):
        if user_id not in self.settings["admin_ids"]:
            self.settings["admin_ids"].append(user_id)
            self._save_settings()

    def get_operator_id(self) -> Optional[int]:
        return self.settings.get("operator_id")

    def set_operator_id(self, user_id: int):
        self.settings["operator_id"] = user_id
        self._save_settings()

    def get_message_text(self) -> str:
        return self.settings.get("message_text", "")

    def set_message_text(self, message: str):
        self.settings["message_text"] = message
        self._save_settings()

    def get_interval_minutes(self) -> int:
        return int(self.settings.get("interval_minutes", 60))

    def set_interval_minutes(self, minutes: int):
        self.settings["interval_minutes"] = int(minutes)
        self._save_settings()

    def get_auto_start(self) -> bool:
        return bool(self.settings.get("auto_start", False))

    def get_auto_restart(self) -> bool:
        return bool(self.settings.get("auto_restart", True))

    def get_owner_info(self) -> Dict[str, str]:
        return self.settings.get("owner_info", {})

    def set_owner_info(self, info: Dict[str, str]):
        self.settings["owner_info"] = info
        self._save_settings()

    def get_groups(self) -> List[int]:
        return self.groups_data.get("groups", [])

    def add_group(self, group_id: int):
        if group_id not in self.groups_data["groups"]:
            self.groups_data["groups"].append(group_id)
            self._save_groups()

    def remove_group(self, group_id: int):
        if group_id in self.groups_data["groups"]:
            self.groups_data["groups"].remove(group_id)
            self._save_groups()
