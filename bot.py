# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from config import BOT_TOKEN, ADMIN_ID
from database import Database
from keyboards import get_main_keyboard, get_admin_keyboard, get_confirm_keyboard

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()

# Состояния FSM
class Form(StatesGroup):
    waiting_for_address = State()
    waiting_for_gift_code = State()
    admin_message = State()

# Команда /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎅 Добро пожаловать в Тайного Санту! 🎄\n\n"
        "Я помогу организовать обмен подарками. Вот что вы можете сделать:\n\n"
        "🎅 Стать участником - зарегистрироваться в игре\n"
        "📦 Указать адрес доставки - куда отправить вам подарок\n"
        "🎁 Узнать своего получателя - после жеребьевки\n"
        "🔐 Отправить код подарка - чтобы получатель мог забрать подарок\n\n"
        "Для администрирования используйте /admin",
        reply_markup=get_main_keyboard()
    )
    
    # Регистрируем пользователя в базе
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    db.add_participant(user_id, username, full_name)

# Команда /admin (только для администратора)
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("У вас нет прав администратора!")
        return
    
    await message.answer(
        "Панель администратора:",
        reply_markup=get_admin_keyboard()
    )

# Кнопка "Стать участником"
@dp.message(F.text == "🎅 Стать участником")
async def become_participant(message: Message):
    participant = db.get_participant(message.from_user.id)
    if participant:
        await message.answer(
            "✅ Вы уже зарегистрированы как участник!\n"
            f"Ваше имя: {participant[2]}\n"
            "Не забудьте указать адрес доставки!",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "🎅 Отлично! Вы хотите стать участником Тайного Санты?\n\n"
            "Правила:\n"
            "1. Вы получите имя другого участника\n"
            "2. Пришлете ему подарок\n"
            "3. Получите подарок от своего Тайного Санты\n\n"
            "Подтвердите участие:",
            reply_markup=get_confirm_keyboard()
        )

# Подтверждение участия
@dp.callback_query(F.data == "confirm_participation")
async def confirm_participation(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name
    
    db.add_participant(user_id, username, full_name)
    
    await callback.message.edit_text(
        "🎉 Поздравляем! Вы стали участником Тайного Санты!\n\n"
        "Теперь укажите адрес доставки, куда ваш Санта сможет отправить подарок."
    )
    await callback.answer()

# Кнопка "Указать адрес доставки"
@dp.message(F.text == "📦 Указать адрес доставки")
async def request_address(message: Message, state: FSMContext):
    await message.answer(
        "📝 Пожалуйста, введите ваш адрес доставки в формате:\n"
        "Город, улица, дом, квартира, индекс\n\n"
        "Пример: Москва, ул. Пушкина, д. 10, кв. 5, 123456"
    )
    await state.set_state(Form.waiting_for_address)

# Получение адреса
@dp.message(Form.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    address = message.text
    db.update_address(message.from_user.id, address)
    
    await message.answer(
        "✅ Адрес успешно сохранен!\n"
        "Теперь ваш Тайный Санта знает, куда отправить подарок.",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

# Кнопка "Узнать своего получателя"
@dp.message(F.text == "🎁 Узнать своего получателя")
async def get_recipient_info(message: Message):
    user_id = message.from_user.id
    
    if not db.is_draw_completed():
        await message.answer("Жеребьевка еще не проведена! Ожидайте начала.")
        return
    
    recipient = db.get_recipient(user_id)
    if not recipient:
        await message.answer("Вы не участвуете в текущей жеребьевке.")
        return
    
    # Отправляем информацию о получателе (без адреса, если он еще не указан)
    recipient_info = (
        f"🎅 Ваш получатель: {recipient[2]}\n"
        f"👤 Username: @{recipient[1] if recipient[1] else 'не указан'}\n"
    )
    
    # Проверяем, указал ли получатель адрес
    if recipient[3]:  # address
        recipient_info += f"📦 Адрес доставки: {recipient[3]}"
    else:
        recipient_info += "📦 Адрес еще не указан. Напомните получателю указать адрес!"
    
    await message.answer(recipient_info)

# Кнопка "Отправить код подарка"
@dp.message(F.text == "🔐 Отправить код подарка")
async def request_gift_code(message: Message, state: FSMContext):
    await message.answer(
        "🔐 Введите код/трек-номер для получения вашего подарка:\n\n"
        "Это может быть:\n"
        "• Трек-номер почтового отправления\n"
        "• Код для получения в пункте выдачи\n"
        "• Другой идентификатор подарка"
    )
    await state.set_state(Form.waiting_for_gift_code)

# Получение кода подарка и пересылка получателю
@dp.message(Form.waiting_for_gift_code)
async def process_gift_code(message: Message, state: FSMContext):
    gift_code = message.text
    santa_id = message.from_user.id
    
    # Сохраняем код в базе
    db.update_gift_code(santa_id, gift_code)
    
    # Получаем информацию о получателе
    recipient = db.get_recipient(santa_id)
    
    if recipient and recipient[0]:  # recipient[0] = user_id
        recipient_id = recipient[0]
        
        # Получаем информацию о санте
        santa_info = db.get_participant(santa_id)
        
        # Отправляем код получателю
        try:
            await bot.send_message(
                recipient_id,
                f"🎁 Ваш Тайный Санта отправил вам подарок!\n\n"
                f"🔐 Код для получения: {gift_code}\n"
                f"🎅 От: {santa_info[2]} (@{santa_info[1] if santa_info[1] else 'username не указан'})"
            )
            await message.answer(
                "✅ Код подарка успешно отправлен вашему получателю!",
                reply_markup=get_main_keyboard()
            )
        except Exception as e:
            await message.answer(
                "⚠️ Не удалось отправить код получателю. "
                "Возможно, он заблокировал бота.",
                reply_markup=get_main_keyboard()
            )
            logger.error(f"Failed to send message to {recipient_id}: {e}")
    else:
        await message.answer(
            "❌ Не найден получатель. Обратитесь к администратору.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()

# Админ: список участников
@dp.message(F.text == "👥 Список участников")
async def list_participants(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    participants = db.get_all_participants()
    
    if not participants:
        await message.answer("Участников пока нет.")
        return
    
    response = "📋 Список участников:\n\n"
    for p in participants:
        status = "✅" if p[3] else "❌"  # p[3] = address
        response += f"{p[2]} (@{p[1]}) - Адрес: {status}\n"
    
    await message.answer(response)

# Админ: провести жеребьевку
@dp.message(F.text == "🎲 Провести жеребьевку")
async def perform_draw(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    participants = db.get_all_participants()
    
    if len(participants) < 2:
        await message.answer("❌ Для жеребьевки нужно минимум 2 участника!")
        return
    
    success = db.perform_draw()
    
    if success:
        # Отправляем каждому участнику информацию о его получателе
        for participant in participants:
            user_id = participant[0]
            recipient = db.get_recipient(user_id)
            
            if recipient:
                try:
                    await bot.send_message(
                        user_id,
                        f"🎉 Жеребьевка проведена!\n\n"
                        f"🎅 Ваш получатель: {recipient[2]}\n"
                        f"👤 @{recipient[1] if recipient[1] else 'username не указан'}\n\n"
                        "Теперь вы можете отправить подарок!"
                    )
                except Exception as e:
                    logger.error(f"Failed to notify {user_id}: {e}")
        
        await message.answer(
            f"✅ Жеребьевка успешно проведена для {len(participants)} участников!\n"
            "Все участники получили уведомления."
        )
    else:
        await message.answer("❌ Ошибка при проведении жеребьевки!")

# Админ: сделать рассылку
@dp.message(F.text == "📢 Сделать рассылку")
async def start_broadcast(message: Message, state: FSMContext):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    await message.answer(
        "Введите сообщение для рассылки всем участникам:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Form.admin_message)

# Обработка рассылки
@dp.message(Form.admin_message)
async def process_broadcast(message: Message, state: FSMContext):
    participants = db.get_all_participants()
    sent = 0
    failed = 0
    
    for participant in participants:
        try:
            await bot.send_message(
                participant[0],  # user_id
                f"📢 Сообщение от организатора:\n\n{message.text}"
            )
            sent += 1
            await asyncio.sleep(0.05)  # Защита от лимитов Telegram
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send to {participant[0]}: {e}")
    
    await message.answer(
        f"✅ Рассылка завершена:\n"
        f"• Отправлено: {sent}\n"
        f"• Не удалось: {failed}",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

# Кнопка "Назад" для админа
@dp.message(F.text == "◀️ Назад")
async def back_to_main(message: Message):
    await cmd_start(message)

# Кнопка "Помощь"
@dp.message(F.text == "ℹ️ Помощь")
async def show_help(message: Message):
    help_text = (
        "🎅 Помощь по Тайному Санте 🎄\n\n"
        "Как это работает:\n"
        "1. Нажмите '🎅 Стать участником'\n"
        "2. Укажите '📦 Адрес доставки'\n"
        "3. После жеребьевки нажмите '🎁 Узнать своего получателя'\n"
        "4. Отправьте подарок получателю\n"
        "5. Нажмите '🔐 Отправить код подарка'\n\n"
        "Ваш Санта также отправит вам код для получения подарка!\n\n"
        "Вопросы? Обращайтесь к организатору."
    )
    await message.answer(help_text)

# Основная функция
async def main():
    print("Бот Тайный Санта запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())