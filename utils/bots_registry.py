import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from .config import Config
from .licensing import LicenseManager

class BotRegistry:
    """
    Enhanced Bot Registry with per-bot proxy configurations
    Stores data in config/bots.json with per-bot settings including SOCKS5 proxy
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

    def _default_bot(self, name: str) -> Dict[str, Any]:
        return {
            "name": name,
            "token_encrypted": "",
            "license_key": None,
            "license_status": "inactive",
            "created_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "proxy_config": {
                "enabled": False,
                "type": "socks5",
                "host": "127.0.0.1",
                "port": 1080,
                "username": "",
                "password_encrypted": ""
            },
            "groups": [],
            "message_templates": {
                "active_template": "default",
                "templates": {
                    "default": "🤖 Bot message from {bot_name}: {timestamp}"
                }
            },
            "settings": {
                "interval_minutes": 60,
                "auto_start": False,
                "auto_restart": True
            }
        }

    def _load(self):
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    self.registry = json.load(f)
                # Migrate old bots without proxy_config
                self._migrate_bots()
            except Exception:
                self.registry = self._default()
        else:
            self.registry = self._default()
            self._save()

    def _migrate_bots(self):
        """Migrate old bot entries to include proxy_config and other new fields"""
        migrated = False
        for bot_id, bot_data in self.registry.get('bots', {}).items():
            if 'proxy_config' not in bot_data:
                bot_data['proxy_config'] = self._default_bot("")["proxy_config"]
                migrated = True
            if 'created_date' not in bot_data:
                bot_data['created_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                migrated = True
            if 'message_templates' not in bot_data:
                bot_data['message_templates'] = self._default_bot("")["message_templates"]
                migrated = True
            if 'settings' not in bot_data:
                bot_data['settings'] = self._default_bot("")["settings"]
                migrated = True
        
        if migrated:
            self._save()

    def _save(self):
        try:
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving bot registry: {e}")

    # CRUD operations
    def list_bots(self) -> List[str]:
        return list(self.registry.get('bots', {}).keys())

    def get_active_bot(self) -> Optional[str]:
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
        
        self.registry['bots'][bot_id] = self._default_bot(name)
        if token_encrypted:
            self.registry['bots'][bot_id]['token_encrypted'] = token_encrypted
            
        if not self.registry.get('active_bot'):
            self.registry['active_bot'] = bot_id
            
        self._save()
        return True

    def remove_bot(self, bot_id: str) -> bool:
        if bot_id in self.registry.get('bots', {}):
            del self.registry['bots'][bot_id]
            if self.registry.get('active_bot') == bot_id:
                remaining_bots = list(self.registry['bots'].keys())
                self.registry['active_bot'] = remaining_bots[0] if remaining_bots else None
            self._save()
            return True
        return False

    def get_bot(self, bot_id: str) -> Dict[str, Any]:
        return self.registry['bots'].get(bot_id, {})

    def update_bot(self, bot_id: str, **kwargs) -> bool:
        """Update bot data with arbitrary fields"""
        if bot_id not in self.registry.get('bots', {}):
            return False
        
        for key, value in kwargs.items():
            self.registry['bots'][bot_id][key] = value
        
        self._save()
        return True

    # License management
    def set_license(self, bot_id: str, license_key: str) -> Dict[str, Any]:
        bot = self.registry['bots'].get(bot_id)
        if not bot:
            return {"ok": False, "reason": "bot not found"}
            
        # Validate license - use global config token for now
        cfg = Config()
        token = cfg.get_bot_token()
        if not token:
            return {"ok": False, "reason": "no bot token configured"}
            
        status = self.licenser.validate_key(license_key, bot_token=token, hwid=self.licenser.get_hwid())
        bot['license_key'] = license_key
        bot['license_status'] = 'active' if status['valid'] else f"invalid: {status.get('reason')}"
        self._save()
        return {"ok": status['valid'], "status": status}

    # Per-bot proxy configuration
    def get_bot_proxy_config(self, bot_id: str) -> Dict[str, Any]:
        """Get proxy configuration for specific bot"""
        bot = self.get_bot(bot_id)
        return bot.get('proxy_config', {
            "enabled": False,
            "type": "socks5",
            "host": "127.0.0.1",
            "port": 1080,
            "username": "",
            "password_encrypted": ""
        })

    def set_bot_proxy_config(self, bot_id: str, enabled: bool, host: str = "127.0.0.1", 
                            port: int = 1080, username: str = "", password: str = "", 
                            proxy_type: str = "socks5") -> bool:
        """Set proxy configuration for specific bot with encrypted password"""
        bot = self.registry['bots'].get(bot_id)
        if not bot:
            return False
            
        # Encrypt password using global config encryption
        password_encrypted = ""
        if password:
            try:
                cfg = Config()
                from cryptography.fernet import Fernet
                import base64
                cipher = cfg._cipher()
                enc = cipher.encrypt(password.encode())
                password_encrypted = base64.b64encode(enc).decode()
            except Exception:
                pass  # Keep empty if encryption fails
        
        bot['proxy_config'] = {
            "enabled": enabled,
            "type": proxy_type,
            "host": host,
            "port": int(port),
            "username": username,
            "password_encrypted": password_encrypted
        }
        
        self._save()
        return True

    def get_bot_proxy_password(self, bot_id: str) -> str:
        """Get decrypted proxy password for specific bot"""
        proxy = self.get_bot_proxy_config(bot_id)
        password_encrypted = proxy.get("password_encrypted", "")
        if not password_encrypted:
            return ""
            
        try:
            cfg = Config()
            from cryptography.fernet import Fernet
            import base64
            cipher = cfg._cipher()
            enc = base64.b64decode(password_encrypted)
            return cipher.decrypt(enc).decode()
        except Exception:
            return ""

    # Per-bot groups (future enhancement)
    def get_bot_groups(self, bot_id: str) -> List[Dict[str, Any]]:
        """Get groups for specific bot (fallback to global for now)"""
        bot = self.get_bot(bot_id)
        return bot.get('groups', [])

    def set_bot_groups(self, bot_id: str, groups: List[Dict[str, Any]]) -> bool:
        """Set groups for specific bot"""
        return self.update_bot(bot_id, groups=groups)

    # Per-bot templates (future enhancement)
    def get_bot_templates(self, bot_id: str) -> Dict[str, Any]:
        """Get message templates for specific bot"""
        bot = self.get_bot(bot_id)
        return bot.get('message_templates', {
            "active_template": "default",
            "templates": {"default": "🤖 Message from {bot_name}: {timestamp}"}
        })

    def set_bot_templates(self, bot_id: str, templates: Dict[str, Any]) -> bool:
        """Set message templates for specific bot"""
        return self.update_bot(bot_id, message_templates=templates)
