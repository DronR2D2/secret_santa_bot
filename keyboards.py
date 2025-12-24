from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Основная клавиатура
def get_main_keyboard():
    """
    Создает и возвращает основную клавиатуру для пользователя.
    """
    keyboard = [
        [KeyboardButton(text="🎅 Стать участником")],
        [KeyboardButton(text="📦 Указать адрес доставки")],
        [KeyboardButton(text="🎁 Узнать своего получателя")],
        [KeyboardButton(text="📦 Отправить QR-код и адрес выдачи")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )

# Клавиатура администратора
def get_admin_keyboard():
    """
    Создает и возвращает клавиатуру для администратора.
    """
    keyboard = [
        [KeyboardButton(text="👥 Список участников")],
        [KeyboardButton(text="🎲 Провести жеребьевку")],
        [KeyboardButton(text="📢 Сделать рассылку")],
        [KeyboardButton(text="◀️ Назад")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Панель управления..."
    )

# Инлайн кнопка для подтверждения участия
def get_confirm_keyboard():
    """
    Создает и возвращает инлайн-клавиатуру для подтверждения участия.
    """
    buttons = [
        [InlineKeyboardButton(text="✅ Да, я участвую!", callback_data="confirm_participation")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Клавиатура только с кнопкой отмены (для FSM состояний)
def get_cancel_keyboard():
    """
    Создает простую клавиатуру с кнопкой отмены.
    Полезна для состояний, где пользователь вводит текст.
    """
    keyboard = [
        [KeyboardButton(text="❌ Отмена")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True  # Скрывается после нажатия
    )