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
        self.key_file = os.path.join(config_dir, ".key")
        self.logger = logging.getLogger(__name__)
        os.makedirs(config_dir, exist_ok=True)
        self._ensure_encryption_key()
        self._load_or_create_config()
        self._migrate_groups_if_needed()

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
                },
                "proxy": {
                    "enabled": False,
                    "type": "socks5",
                    "host": "127.0.0.1",
                    "port": 1080,
                    "username": "",
                    "password_encrypted": ""
                }
            }
            self._save_settings()
        
        # Ensure proxy config exists
        if "proxy" not in self.settings:
            self.settings["proxy"] = {
                "enabled": False,
                "type": "socks5",
                "host": "127.0.0.1",
                "port": 1080,
                "username": "",
                "password_encrypted": ""
            }
            self._save_settings()
        
        if os.path.exists(self.groups_file):
            with open(self.groups_file, 'r', encoding='utf-8') as f:
                self.groups_data = json.load(f)
        else:
            self.groups_data = {"groups": []}
            self._save_groups()

    def _migrate_groups_if_needed(self):
        """Migrate old format [int, int] to new format [{'id': int, 'name': str, 'interval': int}, ...]"""
        groups = self.groups_data.get("groups", [])
        if not groups:
            return
        
        # Check if migration needed (first item is int)
        if isinstance(groups[0], int):
            self.logger.info("Migrating groups from old format to new object format")
            migrated = []
            for gid in groups:
                migrated.append({
                    "id": int(gid),
                    "name": None,
                    "interval": None
                })
            self.groups_data["groups"] = migrated
            self._save_groups()
            self.logger.info(f"Migrated {len(migrated)} groups to new format")

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

    # NEW GROUP METHODS - Object format with name and interval
    def get_groups_objects(self) -> List[Dict[str, Any]]:
        """Get groups as list of objects: [{'id': int, 'name': str, 'interval': int}, ...]"""
        return self.groups_data.get("groups", [])

    def get_groups(self) -> List[int]:
        """Backward compatibility - returns list of IDs"""
        groups = self.get_groups_objects()
        return [g["id"] for g in groups]

    def add_group(self, group_id: int, name: Optional[str] = None, interval: Optional[int] = None) -> bool:
        """Add group, returns False if already exists (duplicate)"""
        groups = self.get_groups_objects()
        # Check for duplicates
        for g in groups:
            if g["id"] == group_id:
                return False  # Duplicate
        
        groups.append({
            "id": group_id,
            "name": name,
            "interval": interval
        })
        self.groups_data["groups"] = groups
        self._save_groups()
        return True

    def remove_group(self, group_id: int) -> bool:
        """Remove group by ID, returns True if found and removed"""
        groups = self.get_groups_objects()
        original_len = len(groups)
        groups = [g for g in groups if g["id"] != group_id]
        if len(groups) < original_len:
            self.groups_data["groups"] = groups
            self._save_groups()
            return True
        return False

    def update_group(self, group_id: int, name: Optional[str] = None, interval: Optional[int] = None) -> bool:
        """Update group name/interval, returns True if found"""
        groups = self.get_groups_objects()
        for g in groups:
            if g["id"] == group_id:
                if name is not None:
                    g["name"] = name
                if interval is not None:
                    g["interval"] = interval
                self.groups_data["groups"] = groups
                self._save_groups()
                return True
        return False

    def get_group_by_id(self, group_id: int) -> Optional[Dict[str, Any]]:
        """Get single group object by ID"""
        for g in self.get_groups_objects():
            if g["id"] == group_id:
                return g
        return None

    def deduplicate_groups(self) -> int:
        """Remove duplicate group IDs, returns count removed"""
        groups = self.get_groups_objects()
        seen_ids = set()
        unique_groups = []
        removed_count = 0
        
        for g in groups:
            if g["id"] not in seen_ids:
                seen_ids.add(g["id"])
                unique_groups.append(g)
            else:
                removed_count += 1
        
        if removed_count > 0:
            self.groups_data["groups"] = unique_groups
            self._save_groups()
            self.logger.info(f"Removed {removed_count} duplicate groups")
        
        return removed_count

    # PROXY METHODS
    def get_proxy_config(self) -> Dict[str, Any]:
        """Get proxy configuration"""
        return self.settings.get("proxy", {
            "enabled": False,
            "type": "socks5",
            "host": "127.0.0.1",
            "port": 1080,
            "username": "",
            "password_encrypted": ""
        })

    def set_proxy_config(self, enabled: bool, host: str = "127.0.0.1", port: int = 1080, 
                        username: str = "", password: str = "", proxy_type: str = "socks5"):
        """Set proxy configuration with encrypted password"""
        password_encrypted = ""
        if password:
            enc = self._cipher().encrypt(password.encode())
            password_encrypted = base64.b64encode(enc).decode()
        
        self.settings["proxy"] = {
            "enabled": enabled,
            "type": proxy_type,
            "host": host,
            "port": int(port),
            "username": username,
            "password_encrypted": password_encrypted
        }
        self._save_settings()

    def get_proxy_password(self) -> str:
        """Get decrypted proxy password"""
        proxy = self.get_proxy_config()
        password_encrypted = proxy.get("password_encrypted", "")
        if not password_encrypted:
            return ""
        try:
            enc = base64.b64decode(password_encrypted)
            return self._cipher().decrypt(enc).decode()
        except Exception:
            return ""
