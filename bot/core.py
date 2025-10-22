import asyncio
import logging
import ssl
import certifi
import aiohttp
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
from utils.bots_registry import BotRegistry
from utils.licensing import LicenseManager
from bot.menus import MenuSystem
from bot.commands import AdminCommands
from bot.formatting import MessageFormatter
from bot.security import SecurityManager

class TelegramBot:
    def __init__(self):
        self.config = Config()
        self.registry = BotRegistry()
        self.licenser = LicenseManager()
        self.logger = setup_logger()
        self.time_sync = TimeSync()
        self.menu_system = MenuSystem()
        self.formatter = MessageFormatter()
        self.security = SecurityManager()
        self.admin_commands = AdminCommands(self)

        self.application: Optional[Application] = None
        self.is_running = False
        self.group_jobs: Dict[int, Any] = {}
        self.active_bot_id: Optional[str] = None

    def _check_license(self) -> bool:
        """Check license for active bot"""
        token = self.security.get_secure_token()
        active_id = self.registry.get_active_bot()
        
        if not active_id:
            self.logger.warning("No active bot in registry; proceed without license gate")
            return True
            
        bot = self.registry.get_bot(active_id)
        key = bot.get("license_key")
        
        if not key:
            self.logger.error(f"License key missing for active bot: {active_id}")
            return False
            
        status = self.licenser.validate_key(key, bot_token=token, hwid=self.licenser.get_hwid())
        
        if not status.get("valid"):
            self.logger.error(f"License invalid for bot {active_id}: {status}")
            return False
            
        self.logger.info(f"License validated for bot {active_id}: expires 20{status.get('expires')}")
        return True

    def _get_active_bot_proxy_config(self) -> Dict[str, Any]:
        """Get proxy configuration for active bot"""
        active_id = self.registry.get_active_bot()
        if not active_id:
            # Fallback to global config for backward compatibility
            return self.config.get_proxy_config()
        
        return self.registry.get_bot_proxy_config(active_id)

    async def initialize(self) -> bool:
        try:
            token = self.security.get_secure_token()
            if not token:
                raise ValueError("Brak waznego tokenu bota")

            if not self._check_license():
                raise ValueError("License check failed - activate license for active bot")

            self.active_bot_id = self.registry.get_active_bot()
            proxy_config = self._get_active_bot_proxy_config()
            builder = Application.builder().token(token)
            
            if proxy_config.get("enabled", False):
                if ProxyConnector is None:
                    self.logger.error("Proxy enabled but aiohttp-socks not installed. Install: pip install aiohttp-socks")
                    self.logger.warning("Continuing without proxy")
                else:
                    try:
                        proxy_url = f"socks5://{proxy_config['host']}:{proxy_config['port']}"
                        connector_kwargs = {"rdns": True}
                        
                        username = proxy_config.get("username", "")
                        if username:
                            password = self.registry.get_bot_proxy_password(self.active_bot_id)
                            connector_kwargs.update({
                                "username": username,
                                "password": password
                            })
                            
                        connector = ProxyConnector.from_url(proxy_url, **connector_kwargs)
                        session = aiohttp.ClientSession(connector=connector)
                        builder = builder.client_session(session)
                        self.logger.info(f"SOCKS5 proxy configured for bot {self.active_bot_id}: {proxy_config['host']}:{proxy_config['port']}")
                    except Exception as e:
                        self.logger.error(f"Failed to configure proxy for bot {self.active_bot_id}, continuing without proxy: {e}")
            else:
                self.logger.info(f"Bot {self.active_bot_id} configured without proxy")

            self.application = builder.build()
            await self._register_handlers()
            self.time_sync.sync_system_time()
            self.logger.info(f"Bot {self.active_bot_id} initialized successfully (license OK)")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed for bot {self.active_bot_id}: {e}")
            return False

    async def _register_handlers(self):
        app = self.application
        app.add_handler(CommandHandler("license", self._cmd_license))
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

    async def _cmd_license(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /license command for bot activation"""
        try:
            if not update.message:
                return
            args = context.args or []
            if not args:
                await update.message.reply_text("Usage: /license TPMB-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX")
                return
                
            key = args[0].strip()
            token = self.security.get_secure_token()
            status = self.licenser.validate_key(key, bot_token=token, hwid=self.licenser.get_hwid())
            
            if not status.get("valid"):
                await update.message.reply_text(f"❌ License invalid: {status.get('reason', 'unknown')}")
                return
                
            # Apply license to active bot
            active_id = self.registry.get_active_bot() or 'default'
            result = self.registry.set_license(active_id, key)
            
            if result.get('ok'):
                await update.message.reply_text(f"✅ License activated for bot: {active_id}\nExpires: 20{status.get('expires')}")
                self.logger.info(f"License activated via Telegram for bot {active_id}")
            else:
                await update.message.reply_text("❌ Failed to activate license")
                
        except Exception as e:
            self.logger.error(f"/license command error: {e}")
            if update.message:
                await update.message.reply_text("❌ Error processing license command")

    async def handle_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.effective_user:
            return
        user_id = update.effective_user.id
        if user_id in self.config.get_admin_ids():
            return
        await self.menu_system.show_welcome_menu(update, context)

    async def start_messaging(self):
        """Start periodic messaging for active bot"""
        await self.stop_messaging()
        
        # Use active bot's groups or fallback to global
        active_id = self.registry.get_active_bot()
        if active_id:
            groups = self.registry.get_bot_groups(active_id)
            if not groups:  # Fallback to global groups
                groups = self.config.get_groups_objects()
        else:
            groups = self.config.get_groups_objects()
        
        global_interval = self.config.get_interval_minutes()
        
        if not groups:
            self.logger.warning(f"No groups configured for bot {active_id}")
            return
            
        for group in groups:
            group_id = group["id"]
            group_interval = group.get("interval") or global_interval
            job = self.application.job_queue.run_repeating(
                partial(self.send_periodic_message_to_group, group_id=group_id),
                interval=timedelta(minutes=group_interval),
                first=timedelta(seconds=10 + len(self.group_jobs) * 2)
            )
            self.group_jobs[group_id] = job
            
        self.is_running = True
        self.logger.info(f"Started messaging for bot {active_id} with {len(self.group_jobs)} groups")

    async def stop_messaging(self):
        for _, job in list(self.group_jobs.items()):
            if job:
                job.schedule_removal()
        self.group_jobs.clear()
        self.is_running = False
        self.logger.info(f"All messaging jobs stopped for bot {self.active_bot_id}")

    async def restart_messaging(self):
        was_running = self.is_running
        await self.stop_messaging()
        if was_running:
            await self.start_messaging()
            self.logger.info(f"Messaging restarted for bot {self.active_bot_id}")

    async def restart_group_job(self, group_id: int):
        if group_id in self.group_jobs:
            job = self.group_jobs[group_id]
            if job:
                job.schedule_removal()
            del self.group_jobs[group_id]
            
        if self.is_running:
            group = self.config.get_group_by_id(group_id)
            if group:
                group_interval = group.get("interval") or self.config.get_interval_minutes()
                job = self.application.job_queue.run_repeating(
                    partial(self.send_periodic_message_to_group, group_id=group_id),
                    interval=timedelta(minutes=group_interval),
                    first=timedelta(seconds=5)
                )
                self.group_jobs[group_id] = job

    async def send_periodic_message_to_group(self, context: ContextTypes.DEFAULT_TYPE, group_id: int):
        try:
            self.time_sync.sync_system_time()
            message_text = self.config.get_message_text()
            if not message_text.strip():
                self.logger.warning(f"No message configured for bot {self.active_bot_id}")
                return
                
            # Format message with bot name
            bot_name = "Unknown"
            if self.active_bot_id:
                bot_data = self.registry.get_bot(self.active_bot_id)
                bot_name = bot_data.get('name', self.active_bot_id)
                
            formatted = self.formatter.format_message(message_text, bot_name=bot_name)
            
            try:
                await context.bot.send_message(
                    chat_id=group_id, 
                    text=formatted, 
                    parse_mode=ParseMode.HTML, 
                    disable_web_page_preview=True
                )
                self.logger.debug(f"Message sent to group {group_id} from bot {self.active_bot_id}")
            except Exception as e:
                self.logger.error(f"Failed to send to {group_id} from bot {self.active_bot_id}: {e}")
                
        except Exception as e:
            self.logger.error(f"Error in periodic message task for group {group_id}, bot {self.active_bot_id}: {e}")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        self.logger.error(f"Exception in update handler for bot {self.active_bot_id}: {context.error}")
        if not self.is_running and self.config.get_auto_restart():
            self.logger.info(f"Attempting restart for bot {self.active_bot_id} after error in 5s")
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
            self.logger.info(f"Bot {self.active_bot_id} is running with proxy: {self._get_active_bot_proxy_config().get('enabled', False)}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start bot {self.active_bot_id}: {e}")
            return False

    async def shutdown(self):
        self.logger.info(f"Shutting down bot {self.active_bot_id}...")
        await self.stop_messaging()
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        self.logger.info(f"Bot {self.active_bot_id} shutdown complete")
