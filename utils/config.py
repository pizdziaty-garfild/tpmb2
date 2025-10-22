import json
import os
from typing import List, Dict, Any, Optional, Union
from cryptography.fernet import Fernet
import base64
import logging
import shutil
from datetime import datetime

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

    def _ensure_encryption_key(self):
        """Ensure encryption key exists"""
        if not os.path.exists(self.key_file):
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            try:
                os.chmod(self.key_file, 0o600)
            except Exception:
                pass  # Windows doesn't support chmod

    def _cipher(self) -> Fernet:
        """Get encryption cipher"""
        with open(self.key_file, 'rb') as f:
            key = f.read()
        return Fernet(key)

    def _safe_load_json(self, filepath: str, default_content: dict) -> dict:
        """Safely load JSON with backup and recovery"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        raise ValueError("Empty file")
                    return json.loads(content)
            else:
                return default_content
        except Exception as e:
            # Backup corrupted file
            if os.path.exists(filepath):
                backup_path = f"{filepath}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                try:
                    shutil.copy2(filepath, backup_path)
                    self.logger.warning(f"Corrupted config backed up to: {backup_path}")
                except Exception:
                    pass
            
            self.logger.error(f"Failed to load {filepath}: {e}. Using defaults.")
            return default_content

    def _safe_save_json(self, filepath: str, data: dict):
        """Safely save JSON with atomic write"""
        try:
            # Write to temporary file first
            temp_path = filepath + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic move
            if os.path.exists(filepath):
                os.replace(temp_path, filepath)
            else:
                os.rename(temp_path, filepath)
                
        except Exception as e:
            self.logger.error(f"Failed to save {filepath}: {e}")
            # Cleanup temp file if it exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise

    def _load_or_create_config(self):
        """Load or create main configuration"""
        default_settings = {
            "bot_token_encrypted": "",
            "admin_ids": [],
            "operator_id": None,
            "message_text": "🤖 Automatyczna wiadomość! Czas: {timestamp}",
            "interval_minutes": 60,
            "auto_start": False,
            "auto_restart": True,
            "owner_info": {
                "username": "bot_owner",
                "description": "Administrator bota",
                "additional_info": "Skontaktuj się w razie pytań"
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
        
        self.settings = self._safe_load_json(self.settings_file, default_settings)
        
        # Ensure proxy config exists (migration)
        if "proxy" not in self.settings:
            self.settings["proxy"] = default_settings["proxy"]
            self._save_settings()
        
        # Load groups
        default_groups = {"groups": []}
        self.groups_data = self._safe_load_json(self.groups_file, default_groups)

    def _load_or_create_templates(self):
        """Load or create message templates"""
        default_templates = {
            "active_template": "default",
            "templates": {
                "default": "🤖 Automatyczna wiadomość! Czas: {timestamp}",
                "promo": "🔥 PROMOCJA! Dzisiaj {date} o {time}!",
                "info": "ℹ️ Informacja: {timestamp}",
                "announcement": "📢 Ogłoszenie: {message} | {timestamp}"
            }
        }
        
        self.templates = self._safe_load_json(self.templates_file, default_templates)
        
        # Ensure required structure
        if "active_template" not in self.templates:
            self.templates["active_template"] = "default"
        if "templates" not in self.templates:
            self.templates["templates"] = default_templates["templates"]
        
        # Ensure active template exists
        active_key = self.templates["active_template"]
        if active_key not in self.templates["templates"]:
            self.templates["active_template"] = "default"
            if "default" not in self.templates["templates"]:
                self.templates["templates"]["default"] = default_templates["templates"]["default"]
        
        self._save_templates()

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
        """Save main settings"""
        self._safe_save_json(self.settings_file, self.settings)

    def _save_groups(self):
        """Save groups data"""
        self._safe_save_json(self.groups_file, self.groups_data)

    def _save_templates(self):
        """Save templates data"""
        self._safe_save_json(self.templates_file, self.templates)

    # Token management
    def set_bot_token(self, token: str):
        """Set encrypted bot token"""
        enc = self._cipher().encrypt(token.encode())
        self.settings["bot_token_encrypted"] = base64.b64encode(enc).decode()
        self._save_settings()

    def get_bot_token(self) -> Optional[str]:
        """Get decrypted bot token"""
        data = self.settings.get("bot_token_encrypted")
        if not data:
            return None
        try:
            enc = base64.b64decode(data)
            return self._cipher().decrypt(enc).decode()
        except Exception:
            return None

    # Admin management
    def get_admin_ids(self) -> List[int]:
        """Get list of admin user IDs"""
        return self.settings.get("admin_ids", [])

    def add_admin_id(self, user_id: int):
        """Add admin user ID"""
        if user_id not in self.settings["admin_ids"]:
            self.settings["admin_ids"].append(user_id)
            self._save_settings()

    def get_operator_id(self) -> Optional[int]:
        """Get operator user ID"""
        return self.settings.get("operator_id")

    def set_operator_id(self, user_id: int):
        """Set operator user ID"""
        self.settings["operator_id"] = user_id
        self._save_settings()

    # Message and timing
    def get_message_text(self) -> str:
        """Get message text from active template"""
        return self.get_active_message_text()

    def set_message_text(self, message: str):
        """Set message text for active template"""
        key = self.get_active_template_key()
        self.set_template(key, message)

    def get_interval_minutes(self) -> int:
        """Get global interval in minutes"""
        return int(self.settings.get("interval_minutes", 60))

    def set_interval_minutes(self, minutes: int):
        """Set global interval in minutes"""
        self.settings["interval_minutes"] = int(minutes)
        self._save_settings()

    # Auto settings
    def get_auto_start(self) -> bool:
        """Get auto-start setting"""
        return bool(self.settings.get("auto_start", False))

    def get_auto_restart(self) -> bool:
        """Get auto-restart setting"""
        return bool(self.settings.get("auto_restart", True))

    # Owner info
    def get_owner_info(self) -> Dict[str, str]:
        """Get owner information"""
        return self.settings.get("owner_info", {})

    def set_owner_info(self, info: Dict[str, str]):
        """Set owner information"""
        self.settings["owner_info"] = info
        self._save_settings()

    # GROUP METHODS - Enhanced with names and intervals
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

    # TEMPLATE METHODS
    def list_templates(self) -> List[str]:
        """Get list of template keys"""
        return list(self.templates.get("templates", {}).keys())

    def get_active_template_key(self) -> str:
        """Get active template key"""
        return self.templates.get("active_template", "default")

    def set_active_template_key(self, key: str):
        """Set active template key"""
        if key in self.templates.get("templates", {}):
            self.templates["active_template"] = key
            self._save_templates()

    def get_active_message_text(self) -> str:
        """Get message text from active template"""
        key = self.get_active_template_key()
        return self.templates.get("templates", {}).get(key, "")

    def set_template(self, key: str, text: str):
        """Set template text"""
        if "templates" not in self.templates:
            self.templates["templates"] = {}
        self.templates["templates"][key] = text
        self._save_templates()

    def get_template(self, key: str) -> str:
        """Get template text by key"""
        return self.templates.get("templates", {}).get(key, "")

    def remove_template(self, key: str) -> bool:
        """Remove template, returns True if removed (cannot remove active)"""
        if key == self.get_active_template_key():
            return False  # Cannot remove active template
        if key in self.templates.get("templates", {}):
            del self.templates["templates"][key]
            self._save_templates()
            return True
        return False

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

    # DIAGNOSTICS
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for diagnostics"""
        return {
            "groups_count": len(self.get_groups()),
            "templates_count": len(self.list_templates()),
            "active_template": self.get_active_template_key(),
            "global_interval": self.get_interval_minutes(),
            "proxy_enabled": self.get_proxy_config().get("enabled", False),
            "auto_start": self.get_auto_start(),
            "auto_restart": self.get_auto_restart(),
            "has_token": bool(self.get_bot_token()),
            "admin_count": len(self.get_admin_ids())
        }
