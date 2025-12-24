import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN, ADMIN_ID
from database import Database
from keyboards import get_main_keyboard, get_admin_keyboard, get_confirm_keyboard, get_cancel_keyboard

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
    waiting_for_qr_photo = State()       # Для фото QR-кода
    waiting_for_pickup_address = State()  # Для адреса пункта выдачи
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
        "📦 Отправить QR-код и адрес выдачи - чтобы получатель мог забрать подарок\n\n"
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
        "Пример: Москва, ул. Пушкина, д. 10, кв. 5, 123456",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(Form.waiting_for_address)

# Получение адреса
@dp.message(Form.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("❌ Ввод адреса отменен.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
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
    
    # Отправляем информацию о получателе
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

# Кнопка "Отправить QR-код и адрес выдачи"
@dp.message(F.text == "📦 Отправить QR-код и адрес выдачи")
async def request_qr_and_address(message: Message, state: FSMContext):
    await message.answer(
        "📦 **Отправка данных для получения подарка**\n\n"
        "1️⃣ **Сначала отправьте фото QR-кода**\n"
        "(сфотографируйте или загрузите готовое изображение)\n\n"
        "2️⃣ **Затем введите адрес пункта выдачи**\n"
        "Формат: Город, адрес пункта, время работы\n\n"
        "Пример QR-кода от СДЭК/Boxberry/Почты России:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(Form.waiting_for_qr_photo)

# Обработка фото QR-кода
@dp.message(Form.waiting_for_qr_photo, F.photo)
async def process_qr_photo(message: Message, state: FSMContext):
    """Сохраняем фото QR-кода и запрашиваем адрес"""
    # Сохраняем file_id фото во временное хранилище
    photo = message.photo[-1]  # Самое качественное фото
    await state.update_data(qr_photo_id=photo.file_id)
    
    await message.answer(
        "✅ **QR-код принят!**\n\n"
        "Теперь введите адрес пункта выдачи:\n\n"
        "**Формат:**\n"
        "• Город\n"
        "• Адрес пункта\n"
        "• Время работы\n"
        "• Дополнительная информация (если нужно)\n\n"
        "Пример:\n"
        "Москва, ул. Тверская, д. 10, ПВЗ СДЭК\n"
        "Пн-Пт: 10:00-20:00, Сб: 11:00-18:00\n"
        "Код для получения: 123-456",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(Form.waiting_for_pickup_address)

# Если отправили не фото в состоянии ожидания QR-кода
@dp.message(Form.waiting_for_qr_photo)
async def wrong_qr_format(message: Message, state: FSMContext):
    """Если отправили не фото"""
    if message.text == "❌ Отмена":
        await message.answer("❌ Отправка QR-кода отменена.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    await message.answer(
        "❌ Пожалуйста, отправьте именно **фото QR-кода**.\n"
        "Нажмите на скрепку 📎 и выберите фото из галереи."
    )

# Обработка адреса пункта выдачи
@dp.message(Form.waiting_for_pickup_address)
async def process_pickup_address(message: Message, state: FSMContext):
    """Получаем адрес и отправляем всё получателю"""
    if message.text == "❌ Отмена":
        await message.answer("❌ Отправка данных отменена.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    pickup_address = message.text
    user_data = await state.get_data()
    qr_photo_id = user_data.get('qr_photo_id')
    
    if not qr_photo_id:
        await message.answer("❌ Ошибка: QR-код не найден. Начните заново.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    santa_id = message.from_user.id
    santa_info = db.get_participant(santa_id)
    
    # Получаем информацию о получателе
    recipient = db.get_recipient(santa_id)
    
    if recipient and recipient[0]:
        recipient_id = recipient[0]
        
        try:
            # Отправляем получателю ВСЁ одним сообщением
            await bot.send_photo(
                chat_id=recipient_id,
                photo=qr_photo_id,
                caption=(
                    "🎁 **ВАШ ПОДАРОК ГОТОВ К ПОЛУЧЕНИЮ!**\n\n"
                    f"🎅 **От Тайного Санты:** {santa_info[2]}\n"
                    f"📱 @{santa_info[1] if santa_info[1] else 'без username'}\n\n"
                    "📍 **АДРЕС ПУНКТА ВЫДАЧИ:**\n"
                    f"{pickup_address}\n\n"
                    "📷 **QR-код прикреплен выше**\n"
                    "Покажите его на кассе для получения посылки.\n\n"
                    "⏰ **Не забудьте взять с собой паспорт!**"
                )
            )
            
            # Сохраняем данные в базу
            db.update_gift_code(santa_id, f"QR+ADDRESS:{qr_photo_id[:20]}...")
            
            await message.answer(
                "✅ **Отлично! Данные отправлены получателю!**\n\n"
                "Ваш получатель получил:\n"
                "• Фото QR-кода\n"
                "• Адрес пункта выдачи\n"
                "• Инструкции по получению\n\n"
                "Теперь осталось только ждать, когда он заберет подарок! 🎄",
                reply_markup=get_main_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            await message.answer(
                "❌ Не удалось отправить данные получателю.\n"
                "Возможно, он заблокировал бота.",
                reply_markup=get_main_keyboard()
            )
    else:
        await message.answer(
            "❌ Получатель не найден. Проверьте, проведена ли жеребьевка.",
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
        gift_status = "🎁" if p[4] else "⏳"  # p[4] = gift_code
        response += f"{p[2]} (@{p[1]}) - Адрес: {status} Подарок: {gift_status}\n"
    
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
                        "Теперь вы можете отправить подарок!\n"
                        "Не забудьте потом отправить QR-код и адрес выдачи."
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
        "🎅 **Помощь по Тайному Санте** 🎄\n\n"
        "**Как это работает:**\n"
        "1. 🎅 **Стать участником** - регистрация в игре\n"
        "2. 📦 **Указать адрес доставки** - куда вам отправят подарок\n"
        "3. 🎁 **Узнать своего получателя** - после жеребьевки\n"
        "4. 📦 **Отправить QR-код и адрес выдачи** - когда отправили подарок\n\n"
        "**Про отправку QR-кода:**\n"
        "• Сфотографируйте QR-код из приложения доставки\n"
        "• Отправьте фото боту\n"
        "• Введите адрес пункта выдачи\n"
        "• Получатель получит всё для получения подарка!\n\n"
        "**Ваш Санта также отправит вам QR-код для получения!**\n\n"
        "Вопросы? Обращайтесь к организатору."
    )
    await message.answer(help_text)

# Обработка команды отмены для всех состояний
@dp.message(F.text == "❌ Отмена")
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=get_main_keyboard()
    )

# Основная функция
async def main():
    print("Бот Тайный Санта запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())