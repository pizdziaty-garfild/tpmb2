import json
import os
from typing import List, Dict, Any, Optional, Union
from cryptography.fernet import Fernet
import base64
import logging

class Config:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.settings_file = os.path.join(config_dir, "settings.json")
        self.groups_file = os.path.join(config_dir, "groups.json")
        self.templates_file = os.path.join(config_dir, "message_templates.json")
        self.key_file = os.path.join(config_dir, ".key")
        self.logger = logging.getLogger(__name__)
        os.makedirs(config_dir, exist_ok=True)
        self._ensure_encryption_key()
        self._load_or_create_config()
        self._migrate_groups_if_needed()
        self._load_or_create_templates()

    # ... existing methods ...

    def _load_or_create_templates(self):
        if os.path.exists(self.templates_file):
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                self.templates = json.load(f)
        else:
            self.templates = {
                "active_template": "default",
                "templates": {
                    "default": "🤖 Automatyczna wiadomosc! Czas: {timestamp}",
                    "promo": "🔥 PROMO! Dzisiaj {date} o {time}!",
                    "info": "ℹ️ Informacja: {timestamp}"
                }
            }
            self._save_templates()

    def _save_templates(self):
        with open(self.templates_file, 'w', encoding='utf-8') as f:
            json.dump(self.templates, f, indent=2, ensure_ascii=False)

    # Template API
    def list_templates(self) -> List[str]:
        return list(self.templates.get("templates", {}).keys())

    def get_active_template_key(self) -> str:
        return self.templates.get("active_template", "default")

    def set_active_template_key(self, key: str):
        if key in self.templates.get("templates", {}):
            self.templates["active_template"] = key
            self._save_templates()

    def get_active_message_text(self) -> str:
        key = self.get_active_template_key()
        return self.templates.get("templates", {}).get(key, "")

    def set_template(self, key: str, text: str):
        if "templates" not in self.templates:
            self.templates["templates"] = {}
        self.templates["templates"][key] = text
        self._save_templates()

    def remove_template(self, key: str) -> bool:
        if key == self.get_active_template_key():
            return False
        if key in self.templates.get("templates", {}):
            del self.templates["templates"][key]
            self._save_templates()
            return True
        return False

    # override old get_message_text to use active template
    def get_message_text(self) -> str:
        return self.get_active_message_text()

    def set_message_text(self, message: str):
        # When user saves message from GUI, store it in the active template
        key = self.get_active_template_key()
        self.set_template(key, message)
