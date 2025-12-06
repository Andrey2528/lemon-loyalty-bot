from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, Contact, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from config import TELEGRAM_TOKEN
from broadcast import register_broadcast_handlers, start_scheduler, is_admin

import db
import asyncio
import logging
import sys
import os
import qrcode
from io import BytesIO
from aiohttp import web

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Конфігурація webhook
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "")  # Ваш домен Koyeb
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

db.init_db()
db.init_promos_table()
db.init_weekly_broadcast_table()

# --- Головне меню ---
def get_main_menu(is_admin=False):
    buttons = [
        [KeyboardButton(text="📱 Мій QR-код")],
        [KeyboardButton(text="💰 Кешбек")],
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
    
    phone = user[0]  # phone is the first element
    
    # Генерація QR-коду локально
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(phone)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Конвертуємо зображення в байти
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        # Відправляємо як BufferedInputFile
        photo = BufferedInputFile(bio.read(), filename="qr_code.png")
        await message.answer_photo(
            photo=photo, 
            caption=f"📷 Ваш QR-код для нарахування бонусів\n\nНомер: <b>{phone}</b>", 
            reply_markup=get_back_menu()
        )
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        await message.answer("❌ Помилка при генерації QR-коду. Спробуйте пізніше.", reply_markup=get_back_menu())

# Інші обробники з оригінального bot.py потрібно скопіювати сюди...

# --- Health Check ---
async def health_check(request):
    """Health check endpoint для Koyeb"""
    return web.Response(text="OK", status=200)

async def on_startup(app):
    """Викликається при запуску"""
    logger.info("Запуск бота в режимі webhook...")
    
    # Реєструємо обробники
    register_broadcast_handlers(dp, bot, get_main_menu)
    start_scheduler(bot)
    
    # Встановлюємо webhook
    if WEBHOOK_HOST:
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True
        )
        logger.info(f"Webhook встановлено: {WEBHOOK_URL}")
    else:
        logger.warning("WEBHOOK_HOST не встановлено, бот працюватиме без webhook")

async def on_shutdown(app):
    """Викликається при зупинці"""
    logger.info("Зупинка бота...")
    await bot.delete_webhook()
    await bot.session.close()

def main():
    """Головна функція запуску"""
    port = int(os.getenv("PORT", 8000))
    
    # Створюємо aiohttp додаток
    app = web.Application()
    
    # Health check endpoints
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    # Webhook handler
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    webhook_handler.register(app, path=WEBHOOK_PATH)
    
    # Startup/shutdown callbacks
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    # Запускаємо сервер
    logger.info(f"Запуск веб-сервера на порту {port}")
    web.run_app(app, host='0.0.0.0', port=port)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"Критична помилка: {e}", exc_info=True)
        sys.exit(1)
