"""Reply keyboards (главное меню)."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.bot import texts


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.MAIN_MENU_CATALOG)],
            [
                KeyboardButton(text=texts.MAIN_MENU_SERVERS),
                KeyboardButton(text=texts.MAIN_MENU_BALANCE),
            ],
            [
                KeyboardButton(text=texts.MAIN_MENU_PROFILE),
                KeyboardButton(text=texts.MAIN_MENU_SUPPORT),
            ],
        ],
        resize_keyboard=True,
    )
