# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Основная клавиатура
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎅 Стать участником")],
            [KeyboardButton(text="📦 Указать адрес доставки")],
            [KeyboardButton(text="🎁 Узнать своего получателя")],
            [KeyboardButton(text="🔐 Отправить код подарка")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard

# Клавиатура администратора
def get_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Список участников")],
            [KeyboardButton(text="🎲 Провести жеребьевку")],
            [KeyboardButton(text="📢 Сделать рассылку")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard

# Инлайн кнопка для подтверждения
def get_confirm_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, я участвую!", callback_data="confirm_participation")]
    ])
    return keyboard