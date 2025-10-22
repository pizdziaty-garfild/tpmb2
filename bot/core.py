import asyncio
import logging
import ssl
import certifi
from datetime import timedelta
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

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
        self.message_job = None

    async def initialize(self) -> bool:
        try:
            token = self.security.get_secure_token()
            if not token:
                raise ValueError("Brak waznego tokenu bota")

            ssl_context = ssl.create_default_context(cafile=certifi.where())
            self.application = Application.builder().token(token).build()

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
        if self.message_job:
            self.message_job.schedule_removal()
        interval = self.config.get_interval_minutes()
        self.message_job = self.application.job_queue.run_repeating(
            self.send_periodic_message,
            interval=timedelta(minutes=interval),
            first=timedelta(seconds=10)
        )
        self.is_running = True
        self.logger.info(f"Wysylanie cykliczne uruchomione: co {interval} min")

    async def stop_messaging(self):
        if self.message_job:
            self.message_job.schedule_removal()
            self.message_job = None
        self.is_running = False
        self.logger.info("Wysylanie cykliczne zatrzymane")

    async def send_periodic_message(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            self.time_sync.sync_system_time()
            groups = self.config.get_groups()
            message_text = self.config.get_message_text()
            if not message_text.strip():
                self.logger.warning("Brak skonfigurowanej wiadomosci")
                return
            formatted = self.formatter.format_message(message_text)
            for gid in groups:
                try:
                    await context.bot.send_message(chat_id=gid, text=formatted, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                    self.logger.info(f"Wiadomosc wyslana do {gid}")
                except Exception as e:
                    self.logger.error(f"Blad wysylania do {gid}: {e}")
        except Exception as e:
            self.logger.error(f"Blad zadania okresowego: {e}")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        self.logger.error(f"Wyjatek podczas obslugi update: {context.error}")
        if not self.is_running and self.config.get_auto_restart():
            self.logger.info("Proba restartu wysylania po bledzie za 5s")
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
            self.logger.info("TPMB2 dziala")
            return True
        except Exception as e:
            self.logger.error(f"Blad uruchomienia bota: {e}")
            return False

    async def shutdown(self):
        self.logger.info("Zamykanie TPMB2...")
        await self.stop_messaging()
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        self.logger.info("Zamknieto TPMB2")
