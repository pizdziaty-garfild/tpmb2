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

    def _check_license(self) -> bool:
        token = self.security.get_secure_token()
        active_id = self.registry.get_active_bot()
        if not active_id:
            self.logger.warning("No active bot in registry; proceed without license gate")
            return True
        bot = self.registry.get_bot(active_id)
        key = bot.get("license_key")
        if not key:
            self.logger.error("License key missing for active bot")
            return False
        status = self.licenser.validate_key(key, bot_token=token, hwid=self.licenser.get_hwid())
        if not status.get("valid"):
            self.logger.error(f"License invalid: {status}")
            return False
        return True

    async def initialize(self) -> bool:
        try:
            token = self.security.get_secure_token()
            if not token:
                raise ValueError("Brak waznego tokenu bota")

            if not self._check_license():
                raise ValueError("License check failed - activate license for active bot")

            proxy_config = self.config.get_proxy_config()
            builder = Application.builder().token(token)
            
            if proxy_config.get("enabled", False):
                if ProxyConnector is None:
                    self.logger.error("Proxy enabled but aiohttp-socks not installed. Install: pip install aiohttp-socks")
                    self.logger.warning("Continuing without proxy")
                else:
                    try:
                        proxy_url = f"socks5://{proxy_config['host']}:{proxy_config['port']}"
                        connector_kwargs = {"rdns": True}
                        if proxy_config.get("username"):
                            pwd = self.config.get_proxy_password()
                            connector_kwargs.update({
                                "username": proxy_config.get("username"),
                                "password": pwd
                            })
                        connector = ProxyConnector.from_url(proxy_url, **connector_kwargs)
                        session = aiohttp.ClientSession(connector=connector)
                        builder = builder.client_session(session)
                        self.logger.info(f"SOCKS5 proxy configured: {proxy_config['host']}:{proxy_config['port']}")
                    except Exception as e:
                        self.logger.error(f"Failed to configure proxy, continuing without proxy: {e}")

            self.application = builder.build()
            await self._register_handlers()
            self.time_sync.sync_system_time()
            self.logger.info("Bot TPMB2 zainicjalizowany (license OK)")
            return True
        except Exception as e:
            self.logger.error(f"Inicjalizacja nieudana: {e}")
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
                await update.message.reply_text(f"❌ License invalid: {status}")
                return
            active_id = self.registry.get_active_bot() or 'default'
            self.registry.set_license(active_id, key)
            await update.message.reply_text("✅ License activated for active bot")
        except Exception as e:
            self.logger.error(f"/license error: {e}")
            if update.message:
                await update.message.reply_text("❌ Error while processing license")

    async def handle_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.effective_user:
            return
        user_id = update.effective_user.id
        if user_id in self.config.get_admin_ids():
            return
        await self.menu_system.show_welcome_menu(update, context)

    async def start_messaging(self):
        await self.stop_messaging()
        groups = self.config.get_groups_objects()
        global_interval = self.config.get_interval_minutes()
        if not groups:
            self.logger.warning("No groups configured")
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
        self.logger.info(f"Started messaging for {len(self.group_jobs)} groups")

    async def stop_messaging(self):
        for _, job in list(self.group_jobs.items()):
            if job:
                job.schedule_removal()
        self.group_jobs.clear()
        self.is_running = False
        self.logger.info("All messaging jobs stopped")

    async def restart_messaging(self):
        was_running = self.is_running
        await self.stop_messaging()
        if was_running:
            await self.start_messaging()
            self.logger.info("Messaging restarted")

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
                self.logger.warning("Brak skonfigurowanej wiadomosci")
                return
            formatted = self.formatter.format_message(message_text)
            try:
                await context.bot.send_message(chat_id=group_id, text=formatted, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            except Exception as e:
                self.logger.error(f"Failed to send to {group_id}: {e}")
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
