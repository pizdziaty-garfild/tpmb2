from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import logging

class AdminCommands:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.logger = logging.getLogger(__name__)

    def _is_authorized(self, user_id: int) -> bool:
        from utils.config import Config
        return user_id in Config().get_admin_ids()

    async def _deny(self, update: Update):
        await update.message.reply_text("<b>Brak uprawnien</b>", parse_mode=ParseMode.HTML)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            return await self._deny(update)
        if self.bot.is_running:
            return await update.message.reply_text("Bot juz dziala", parse_mode=ParseMode.HTML)
        await self.bot.start_messaging()
        await update.message.reply_text("Bot uruchomiony", parse_mode=ParseMode.HTML)

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            return await self._deny(update)
        if not self.bot.is_running:
            return await update.message.reply_text("Bot nie jest uruchomiony", parse_mode=ParseMode.HTML)
        await self.bot.stop_messaging()
        await update.message.reply_text("Bot zatrzymany", parse_mode=ParseMode.HTML)

    async def message_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            return await self._deny(update)
        cfg = self.bot.config
        if context.args:
            new = ' '.join(context.args)
            cfg.set_message_text(new)
            return await update.message.reply_text(f"Zmieniono wiadomosc:\n<code>{new}</code>", parse_mode=ParseMode.HTML)
        current = cfg.get_message_text()
        await update.message.reply_text(f"Aktualna wiadomosc:\n<code>{current}</code>", parse_mode=ParseMode.HTML)

    async def interval_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            return await self._deny(update)
        cfg = self.bot.config
        if context.args:
            try:
                val = int(context.args[0]); assert val >= 1
                cfg.set_interval_minutes(val)
                if self.bot.is_running:
                    await self.bot.stop_messaging(); await self.bot.start_messaging()
                return await update.message.reply_text(f"Interwal: {val} min", parse_mode=ParseMode.HTML)
            except Exception:
                return await update.message.reply_text("Podaj prawidlowa liczbe minut >= 1", parse_mode=ParseMode.HTML)
        await update.message.reply_text(f"Aktualny interwal: {cfg.get_interval_minutes()} min", parse_mode=ParseMode.HTML)

    async def groups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            return await self._deny(update)
        cfg = self.bot.config
        if len(context.args) >= 2:
            action = context.args[0].lower(); arg = context.args[1]
            try:
                gid = int(arg)
            except ValueError:
                return await update.message.reply_text("ID grupy musi byc liczba", parse_mode=ParseMode.HTML)
            if action == 'add':
                cfg.add_group(gid); return await update.message.reply_text(f"Dodano grupe {gid}", parse_mode=ParseMode.HTML)
            if action == 'remove':
                cfg.remove_group(gid); return await update.message.reply_text(f"Usunieto grupe {gid}", parse_mode=ParseMode.HTML)
            return await update.message.reply_text("Uzyj 'add' lub 'remove'", parse_mode=ParseMode.HTML)
        groups = cfg.get_groups()
        if groups:
            content = '\n'.join([f"- {g}" for g in groups])
            return await update.message.reply_text(f"Skonfigurowane grupy:\n\n{content}", parse_mode=ParseMode.HTML)
        return await update.message.reply_text("Brak skonfigurowanych grup", parse_mode=ParseMode.HTML)

    async def operator_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            return await self._deny(update)
        cfg = self.bot.config
        if context.args:
            try:
                oid = int(context.args[0]); cfg.set_operator_id(oid)
                return await update.message.reply_text(f"Ustawiono operatora: {oid}", parse_mode=ParseMode.HTML)
            except ValueError:
                return await update.message.reply_text("ID operatora musi byc liczba", parse_mode=ParseMode.HTML)
        cur = cfg.get_operator_id() or 'Nie ustawiony'
        await update.message.reply_text(f"Operator: {cur}", parse_mode=ParseMode.HTML)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            return await self._deny(update)
        cfg = self.bot.config
        text = (
            f"<b>Status Bota</b>\n\n"
            f"- Status: {'Wlaczony' if self.bot.is_running else 'Wylaczony'}\n"
            f"- Interwal: {cfg.get_interval_minutes()} min\n"
            f"- Liczba grup: {len(cfg.get_groups())}\n"
            f"- Operator: {cfg.get_operator_id() or 'Nie ustawiony'}\n\n"
            f"HTTPS/TLS: OK\n"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
