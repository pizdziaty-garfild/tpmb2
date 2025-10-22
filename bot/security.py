import ssl
import certifi
import requests
import logging
from typing import Optional

class SecurityManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.ssl_context.check_hostname = True

    def get_secure_token(self) -> Optional[str]:
        try:
            from utils.config import Config
            token = Config().get_bot_token()
            if not token or ':' not in token:
                self.logger.error("Nieprawidlowy token bota")
                return None
            return token
        except Exception as e:
            self.logger.error(f"Blad pobierania tokenu: {e}")
            return None
