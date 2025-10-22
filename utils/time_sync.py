import ntplib
import time
import logging
import subprocess
import platform
from datetime import datetime
from typing import Optional

class TimeSync:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ntp_servers = ["pool.ntp.org","time.nist.gov","time.google.com","time.cloudflare.com"]
        self.last_sync: Optional[datetime] = None
        self.offset: float = 0.0

    def get_ntp_time(self) -> Optional[float]:
        for server in self.ntp_servers:
            try:
                client = ntplib.NTPClient()
                resp = client.request(server, timeout=10)
                self.logger.info(f"NTP OK {server}")
                return resp.tx_time
            except Exception as e:
                self.logger.warning(f"NTP fail {server}: {e}")
        self.logger.error("NTP: brak odpowiedzi")
        return None

    def sync_system_time(self) -> bool:
        ts = self.get_ntp_time()
        if ts is None:
            return False
        try:
            self.offset = ts - time.time()
            self.last_sync = datetime.now()
            if platform.system() == "Windows" and abs(self.offset) > 1.0:
                try:
                    dt = datetime.fromtimestamp(ts)
                    subprocess.run(['time', dt.strftime('%H:%M:%S')], check=False, shell=True)
                    subprocess.run(['date', dt.strftime('%m-%d-%Y')], check=False, shell=True)
                except Exception:
                    self.logger.warning("Aktualizacja czasu wymaga uprawnien admin")
            return True
        except Exception as e:
            self.logger.error(f"Time sync error: {e}")
            return False
