from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import logging

class MenuSystem:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def show_welcome_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("Info o wlascicielu", callback_data="info_owner")],
            [InlineKeyboardButton("Zobacz wiadomosc", callback_data="show_message")],
            [InlineKeyboardButton("Czat z operatorem", callback_data="encrypted_chat")],
            [InlineKeyboardButton("Pomoc", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        welcome_text = (
            "<b>Witaj w systemie bota!</b>\n\n"
            "- <b>Informacje o wlascicielu</b>\n"
            "- <b>Zobacz wiadomosc</b>\n"
            "- <b>Szyfrowany czat</b>\n"
            "- <b>Pomoc</b>\n\n"
            "<i>Wybierz przycisk aby kontynuowac...</i>"
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(text=welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(text=welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        if data == "info_owner":
            await self.show_owner_info(update, context)
        elif data == "show_message":
            await self.show_current_message(update, context)
        elif data == "encrypted_chat":
            await self.start_encrypted_chat(update, context)
        elif data == "help":
            await self.show_help(update, context)
        elif data == "back_to_main":
            await self.show_welcome_menu(update, context)
        else:
            await query.edit_message_text("Nieznana opcja menu")

    async def show_owner_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from utils.config import Config
        config = Config()
        owner = config.get_owner_info()
        info_text = (
            f"<b>Informacje o wlascicielu</b>\n\n"
            f"<b>Telegram:</b> @{owner.get('username', 'brak')}\n"
            f"<b>Opis:</b> {owner.get('description', 'Brak opisu')}\n\n"
            f"{owner.get('additional_info', '')}"
        )
        back = InlineKeyboardMarkup([[InlineKeyboardButton("<< Powrot", callback_data="back_to_main")]])
        await update.callback_query.edit_message_text(text=info_text, reply_markup=back, parse_mode=ParseMode.HTML)

    async def show_current_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from utils.config import Config
        from bot.formatting import MessageFormatter
        cfg = Config(); fmt = MessageFormatter()
        msg = cfg.get_message_text(); formatted = fmt.format_message(msg)
        preview = (
            "<b>Podglad wiadomosci:</b>\n\n"
            "<code>---------------------</code>\n"
            f"{formatted}\n"
            "<code>---------------------</code>\n\n"
            "<i>Ta wiadomosc jest wysylana automatycznie na wszystkie skonfigurowane grupy.</i>"
        )
        back = InlineKeyboardMarkup([[InlineKeyboardButton("<< Powrot", callback_data="back_to_main")]])
        await update.callback_query.edit_message_text(text=preview, reply_markup=back, parse_mode=ParseMode.HTML)

    async def start_encrypted_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from utils.config import Config
        cfg = Config()
        operator_id = cfg.get_operator_id()
        user = update.effective_user
        back = InlineKeyboardMarkup([[InlineKeyboardButton("<< Powrot", callback_data="back_to_main")]])
        if not operator_id:
            await update.callback_query.edit_message_text(text="<b>Operator nie zostal skonfigurowany</b>", reply_markup=back, parse_mode=ParseMode.HTML)
            return
        try:
            await context.bot.send_message(
                chat_id=operator_id,
                text=(
                    "<b>Nowe zadanie szyfrowanego czatu</b>\n\n"
                    f"Uzytkownik: @{user.username or 'brak'}\nID: {user.id}\n"
                    f"Imie: {user.first_name}"
                ),
                parse_mode=ParseMode.HTML
            )
            await update.callback_query.edit_message_text(text="<b>Zadanie wyslane do operatora</b>", reply_markup=back, parse_mode=ParseMode.HTML)
        except Exception:
            await update.callback_query.edit_message_text(text="Nie udalo sie skontaktowac z operatorem", reply_markup=back, parse_mode=ParseMode.HTML)

    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "<b>Pomoc</b>\n\n"
            "Ten bot wysyla automatycznie wiadomosci do skonfigurowanych grup.\n"
            "Uzyj przyciskow by zobaczyc wiecej informacji."
        )
        back = InlineKeyboardMarkup([[InlineKeyboardButton("<< Powrot", callback_data="back_to_main")]])
        await update.callback_query.edit_message_text(text=text, reply_markup=back, parse_mode=ParseMode.HTML)
