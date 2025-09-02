from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, Contact, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from config import TELEGRAM_TOKEN
from broadcast import register_broadcast_handlers, start_scheduler, is_admin

import db
import asyncio
import logging
import sys
import os

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

db.init_db()
db.init_promos_table()

# --- Головне меню ---
def get_main_menu(is_admin=False):
    buttons = [
        [KeyboardButton(text="📱 Мій QR-код")],
        [KeyboardButton(text="💰 Накопичення")],
        [KeyboardButton(text="🍽 Меню закладу")],
        [KeyboardButton(text="🛵 Доставка")],
        [KeyboardButton(text="📅 Забронювати столик")],
        [KeyboardButton(text="🏷 Акції")],
    ]
    if is_admin:
        buttons.insert(0, [KeyboardButton(text="⚙️ Адмін-панель")])
    kb = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    return kb

# --- /start ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    isadm = is_admin(message)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поділитися номером телефону", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer(f"Приємно познайомитись, <b>{message.from_user.first_name}</b>!\n\nТакож додайте свій номер телефону, натиснувши на кнопку нижче 👇", reply_markup=kb)

# --- Обробка контакту ---
@dp.message(lambda m: m.contact is not None)
async def handle_contact(message: Message):
    phone = message.contact.phone_number
    db.add_user(message.from_user.id, phone, 0)
    isadm = is_admin(message)
    await message.answer("Ваш номер телефону успішно збережено\n\nРеєстрацію завершено!", reply_markup=get_main_menu(is_admin=isadm))


# --- Головне меню ---
@dp.message(lambda m: m.text == "‹ Повернутись до меню")
async def back_to_menu(message: Message):
    isadm = is_admin(message)
    await message.answer("🏠 Головне меню:", reply_markup=get_main_menu(is_admin=isadm))


# --- Кнопка повернення до меню ---
def get_back_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="‹ Повернутись до меню")]],
        resize_keyboard=True
    )

# --- Показати QR-код ---
@dp.message(lambda m: m.text == "📱 Мій QR-код")
async def show_qr(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or not user[0]:
        await message.answer("❌ Ви ще не зареєстровані або не вказали номер телефону. Натисніть /start", reply_markup=get_back_menu())
        return
    phone = user[0]
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={phone}"
    await message.answer_photo(photo=qr_url, caption=f"📷 Ваш QR-код для нарахування бонусів\n\nНомер: <b>{phone}</b>", reply_markup=get_back_menu())

# --- Мій профіль ---
@dp.message(lambda m: m.text == "💰 Накопичення")
async def profile(message: Message):
    user = db.get_user(message.from_user.id)
    if not user:
        return await message.answer("❌ Ви ще не зареєстровані. Натисніть /start", reply_markup=get_back_menu())
    # Тимчасово показуємо фіктивний профіль
    text = f"<b>👤 Профіль: {message.from_user.first_name}</b>\n\n"
    text += f"<b>💳 Ваша знижка:</b> 1%\n"
    text += f"⬆️ Прогрес до наступного рівня знижки: 0%\n"
    text += f"✨ Прогрес до безкоштовного кальяну: 0%\n\n"
    text += "🎁 <b>Бонуси:</b> Накопичуйте витрати — отримуйте знижки та безкоштовні кальяни!\n"
    text += "⭐ <b>Переваги:</b> Більша знижка на кожному рівні + приємні сюрпризи для постійних клієнтів."
    await message.answer(text, reply_markup=get_back_menu())

# --- Меню закладу ---
@dp.message(lambda m: m.text == "🍽 Меню закладу")
async def menu_link(message: Message):
    text = f"Меню закладу: "
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Меню закладу", url="https://lemon.choiceqr.com/")],
            [InlineKeyboardButton(text="‹ Повернутись до меню", callback_data="back_to_menu")]
        ]
    )
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True)

# --- Доставка ---
@dp.message(lambda m: m.text == "🛵 Доставка")
async def delivery(message: Message):
    text = "Доставка доступна через Bolt Food!"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Bolt Food", url="https://food.bolt.eu/en-US/990/p/134325-lemon?utm_source=share_provider&utm_medium=product&utm_content=menu_header")],
            [InlineKeyboardButton(text="‹ Повернутись до меню", callback_data="back_to_menu")]
        ]
    )
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True)

# --- Забронювати столик ---
@dp.message(lambda m: m.text == "📅 Забронювати столик")
async def book_table(message: Message):
    text = (
        "Забронювати столик можна за номером телефону: <b>+380 68 123 43 45</b>\n"
        "або написати в дірект Instagram."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Скопіювати номер", callback_data="copy_phone")],
            [InlineKeyboardButton(text="Instagram", url="https://www.instagram.com/lemon.gastrobar.if?igsh=emxlN3dnZW11dWJ4")],
            [InlineKeyboardButton(text="‹ Повернутись до меню", callback_data="back_to_menu")]
        ]
    )
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True)

# --- Акції ---
@dp.message(lambda m: m.text == "🏷 Акції")
async def show_promos(message: Message):
    promos = db.get_promos()
    if promos:
        text = "<b>Актуальні акції:</b>\n"
        for pid, promo in promos:
            text += f"\n{pid}. {promo}"
        await message.answer(text, reply_markup=get_back_menu())
    else:
        await message.answer("Зараз немає актуальних акцій.", reply_markup=get_back_menu())

# --Обробник inline-кнопок
# --- Обробка callback для повернення до меню з inline-кнопки ---
@dp.callback_query(lambda c: c.data == "back_to_menu")
async def inline_back_to_menu(callback: CallbackQuery):
    isadm = is_admin(callback.message)
    await callback.message.edit_text("🏠 Головне меню:", reply_markup=None)
    await callback.message.answer("🏠 Головне меню:", reply_markup=get_main_menu(is_admin=isadm))

# --- Обробка callback для копіювання номера телефону ---
@dp.callback_query(lambda c: c.data == "copy_phone")
async def copy_phone_callback(callback: CallbackQuery):
    await callback.answer("Номер скопійовано!", show_alert=True)
    await callback.message.answer("+380681234345")

async def main():
    logger.info("Бот запускається...")
    try:
        register_broadcast_handlers(dp, bot, get_main_menu)
        start_scheduler(bot)
        logger.info("Бот успішно запущений та готовий до роботи")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Помилка при запуску бота: {e}")
        raise

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Запуск на порту: {port}")
    asyncio.run(main())