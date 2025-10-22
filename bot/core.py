import asyncio
import logging
import ssl
import certifi
aiohttp
from datetime import timedelta
from typing import Optional, Dict, Any
from functools import partial

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

try:
    from aiohttp_socks import ProxyConnector
except ImportError:
    ProxyConnector = None

from utils.config import Config
from utils.logger import setup_logger
from utils.time_sync import TimeSync
from bot.menus import MenuSystem
from bot.commands import AdminCommands
from bot.formatting import MessageFormatter
from bot.security import SecurityManager

class TelegramBot:
    def __init__(self):
        self.config = Config()
        self.logger = setup_logger()
        self.time_sync = TimeSync()
        self.menu_system = MenuSystem()
        self.formatter = MessageFormatter()
        self.security = SecurityManager()
        self.admin_commands = AdminCommands(self)

        self.application: Optional[Application] = None
        self.is_running = False
        # Changed: per-group jobs instead of single job
        self.group_jobs: Dict[int, Any] = {}  # group_id -> job

    async def initialize(self) -> bool:
        try:
            token = self.security.get_secure_token()
            if not token:
                raise ValueError("Brak waznego tokenu bota")

            # Check and setup proxy if enabled
            proxy_config = self.config.get_proxy_config()
            builder = Application.builder().token(token)
            
            if proxy_config.get("enabled", False) and ProxyConnector:
                self.logger.info("Configuring SOCKS5 proxy...")
                try:
                    proxy_url = f"socks5://{proxy_config['host']}:{proxy_config['port']}"
                    proxy_auth = None
                    if proxy_config.get("username"):
                        proxy_password = self.config.get_proxy_password()
                        proxy_auth = aiohttp.BasicAuth(proxy_config["username"], proxy_password)
                    
                    connector = ProxyConnector.from_url(proxy_url, rdns=True)
                    if proxy_auth:
                        connector = ProxyConnector.from_url(proxy_url, rdns=True, proxy_auth=proxy_auth)
                    
                    import aiohttp
                    session = aiohttp.ClientSession(connector=connector)
                    builder = builder.client_session(session)
                    self.logger.info(f"SOCKS5 proxy configured: {proxy_config['host']}:{proxy_config['port']}")
                except Exception as e:
                    self.logger.error(f"Failed to configure proxy: {e}")
                    return False
            elif proxy_config.get("enabled", False):
                self.logger.error("Proxy enabled but aiohttp-socks not available. Install: pip install aiohttp-socks")
                return False
            
            self.application = builder.build()
            await self._register_handlers()
            self.time_sync.sync_system_time()
            self.logger.info("Bot TPMB2 zainicjalizowany")
            return True
        except Exception as e:
            self.logger.error(f"Inicjalizacja nieudana: {e}")
            return False

    async def _register_handlers(self):
        app = self.application
        app.add_handler(CommandHandler("start", self.admin_commands.start_command))
        app.add_handler(CommandHandler("stop", self.admin_commands.stop_command))
        app.add_handler(CommandHandler("message", self.admin_commands.message_command))
        app.add_handler(CommandHandler("interval", self.admin_commands.interval_command))
        app.add_handler(CommandHandler("groups", self.admin_commands.groups_command))
        app.add_handler(CommandHandler("operator", self.admin_commands.operator_command))
        app.add_handler(CommandHandler("status", self.admin_commands.status_command))

        app.add_handler(CallbackQueryHandler(self.menu_system.handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_user_message))
        app.add_error_handler(self.error_handler)

    async def handle_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.effective_user:
            return
        user_id = update.effective_user.id
        if user_id in self.config.get_admin_ids():
            return
        await self.menu_system.show_welcome_menu(update, context)

    async def start_messaging(self):
        """Start messaging jobs for all groups with their individual intervals"""
        await self.stop_messaging()  # Clear any existing jobs
        
        groups = self.config.get_groups_objects()
        global_interval = self.config.get_interval_minutes()
        
        if not groups:
            self.logger.warning("No groups configured")
            return
        
        for group in groups:
            group_id = group["id"]
            group_interval = group.get("interval") or global_interval
            group_name = group.get("name") or f"Group {group_id}"
            
            # Create job for this specific group
            job = self.application.job_queue.run_repeating(
                partial(self.send_periodic_message_to_group, group_id=group_id),
                interval=timedelta(minutes=group_interval),
                first=timedelta(seconds=10 + len(self.group_jobs) * 2)  # Stagger starts
            )
            self.group_jobs[group_id] = job
            self.logger.info(f"Started job for {group_name} ({group_id}): every {group_interval} min")
        
        self.is_running = True
        self.logger.info(f"Started messaging for {len(self.group_jobs)} groups")

    async def stop_messaging(self):
        """Stop all messaging jobs"""
        for group_id, job in self.group_jobs.items():
            if job:
                job.schedule_removal()
        self.group_jobs.clear()
        self.is_running = False
        self.logger.info("All messaging jobs stopped")

    async def restart_messaging(self):
        """Graceful restart: stop and start messaging"""
        was_running = self.is_running
        await self.stop_messaging()
        if was_running:
            await self.start_messaging()
            self.logger.info("Messaging restarted")

    async def restart_group_job(self, group_id: int):
        """Restart job for a specific group"""
        # Stop existing job for this group
        if group_id in self.group_jobs:
            job = self.group_jobs[group_id]
            if job:
                job.schedule_removal()
            del self.group_jobs[group_id]
        
        # Start new job if we're running
        if self.is_running:
            group = self.config.get_group_by_id(group_id)
            if group:
                group_interval = group.get("interval") or self.config.get_interval_minutes()
                group_name = group.get("name") or f"Group {group_id}"
                
                job = self.application.job_queue.run_repeating(
                    partial(self.send_periodic_message_to_group, group_id=group_id),
                    interval=timedelta(minutes=group_interval),
                    first=timedelta(seconds=5)
                )
                self.group_jobs[group_id] = job
                self.logger.info(f"Restarted job for {group_name} ({group_id}): every {group_interval} min")

    async def send_periodic_message_to_group(self, context: ContextTypes.DEFAULT_TYPE, group_id: int):
        """Send message to a specific group"""
        try:
            self.time_sync.sync_system_time()
            message_text = self.config.get_message_text()
            if not message_text.strip():
                self.logger.warning("Brak skonfigurowanej wiadomosci")
                return
            
            formatted = self.formatter.format_message(message_text)
            
            try:
                await context.bot.send_message(
                    chat_id=group_id, 
                    text=formatted, 
                    parse_mode=ParseMode.HTML, 
                    disable_web_page_preview=True
                )
                
                # Get group info for logging
                group = self.config.get_group_by_id(group_id)
                group_name = group.get("name") if group else None
                log_name = f"{group_name} ({group_id})" if group_name else str(group_id)
                self.logger.info(f"Message sent to {log_name}")
                
            except Exception as e:
                group = self.config.get_group_by_id(group_id)
                group_name = group.get("name") if group else None
                log_name = f"{group_name} ({group_id})" if group_name else str(group_id)
                self.logger.error(f"Failed to send to {log_name}: {e}")
                
        except Exception as e:
            self.logger.error(f"Error in periodic message task for group {group_id}: {e}")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        self.logger.error(f"Exception in update handler: {context.error}")
        if not self.is_running and self.config.get_auto_restart():
            self.logger.info("Attempting restart after error in 5s")
            await asyncio.sleep(5)
            await self.start_messaging()

    async def run(self) -> bool:
        if not self.application:
            if not await self.initialize():
                return False
        try:
            await self.application.initialize()
            await self.application.start()
            if self.config.get_auto_start():
                await self.start_messaging()
            await self.application.updater.start_polling()
            self.logger.info("TPMB2 running")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            return False

    async def shutdown(self):
        self.logger.info("Shutting down TPMB2...")
        await self.stop_messaging()
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        self.logger.info("TPMB2 shutdown complete")
