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
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "").rstrip('/')  # Ваш домен Koyeb (прибираємо слеш на кінці)
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Логування для діагностики
logger.info(f"WEBHOOK_HOST: {WEBHOOK_HOST}")
logger.info(f"WEBHOOK_URL: {WEBHOOK_URL}")

# Перевірка URL
if not WEBHOOK_HOST:
    logger.error("❌ WEBHOOK_HOST не встановлено!")
elif not WEBHOOK_HOST.startswith("https://"):
    logger.error("❌ WEBHOOK_HOST повинен починатися з https://")
else:
    logger.info("✅ WEBHOOK_HOST налаштовано правильно")

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
    logger.info(f"👤 /start від користувача {message.from_user.id} (@{message.from_user.username})")
    try:
        isadm = is_admin(message)
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Поділитися номером телефону", request_contact=True)]],
            resize_keyboard=True
        )
        await message.answer(f"Приємно познайомитись, <b>{message.from_user.first_name}</b>!\n\nТакож додайте свій номер телефону, натиснувши на кнопку нижче 👇", reply_markup=kb)
        logger.info(f"✅ Відповідь на /start відправлено користувачу {message.from_user.id}")
    except Exception as e:
        logger.error(f"❌ Помилка в cmd_start: {e}", exc_info=True)

# --- Обробка контакту ---
@dp.message(lambda m: m.contact is not None)
async def handle_contact(message: Message):
    logger.info(f"📞 Отримано контакт від користувача {message.from_user.id}")
    try:
        phone = message.contact.phone_number
        db.add_user(message.from_user.id, phone, 0)
        isadm = is_admin(message)
        await message.answer("Ваш номер телефону успішно збережено\n\nРеєстрацію завершено!", reply_markup=get_main_menu(is_admin=isadm))
        logger.info(f"✅ Контакт збережено для користувача {message.from_user.id}")
    except Exception as e:
        logger.error(f"❌ Помилка в handle_contact: {e}", exc_info=True)


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
    logger.info(f"📱 QR-код запит від користувача {message.from_user.id}")
    try:
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
        logger.info(f"✅ QR-код відправлено користувачу {message.from_user.id}")
    except Exception as e:
        logger.error(f"❌ Помилка генерації QR-коду: {e}", exc_info=True)
        await message.answer("❌ Помилка при генерації QR-коду. Спробуйте пізніше.", reply_markup=get_back_menu())
    except Exception as e:
        logger.error(f"❌ Помилка в show_qr: {e}", exc_info=True)

# --- Мій профіль ---
@dp.message(lambda m: m.text == "💰 Кешбек")
async def profile(message: Message):
    user = db.get_user(message.from_user.id)
    if not user:
        return await message.answer("❌ Ви ще не зареєстровані. Натисніть /start", reply_markup=get_back_menu())
    
    phone, bonus_points, total_spent = user
    
    # Determine cashback rate and status
    if total_spent >= 30000:
        status = "🍋 Silver guest"
        cashback_rate = "10%"
        progress = "Ви досягли максимального рівня!"
    else:
        status = "🍋 Basic guest"
        cashback_rate = "5%"
        remaining = 30000 - total_spent
        progress = f"До Silver guest залишилось: {remaining:,} грн"
    
    text = f"<b>Перший кешбек у гастробарі 🔥</b>\n\n"
    text += f"<b>{status}</b>\n"
    text += f"З кожного замовлення вам накопичується {cashback_rate} від суми чеку.\n"
    text += f"Його можна використати як знижку на наступне замовлення, або накопичувати далі 💳\n\n"
    
    if total_spent >= 30000:
        text += f"Якщо загальна сума ваших замовлень (за весь час) становить більше 30 000 гривень.\n"
        text += f"Ваш кешбек зростає до 10%\n\n"
    else:
        text += f"🍋 <b>Silver guest</b>\n"
        text += f"Якщо загальна сума ваших замовлень (за весь час) становить більше 30 000 гривень.\n"
        text += f"Ваш кешбек зростає до 10%\n\n"
    
    text += f"💰 <b>Ваш поточний баланс:</b> {bonus_points} грн\n"
    text += f"🛍 <b>Загальна сума замовлень:</b> {total_spent:,} грн\n"
    text += f"📈 <b>Прогрес:</b> {progress}\n\n"
    
    text += f"🤔 <b>Як накопичити?</b>\n"
    text += f"Необхідно надати свій QR-код нашому персоналу для сканування. Таким чином, кешбек нарахується на ваш акаунт."
    
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

# --- Обробка callback для повернення до меню з inline-кнопки ---
@dp.callback_query(lambda c: c.data == "back_to_menu")
async def inline_back_to_menu(callback: CallbackQuery):
    isadm = is_admin(callback.message)
    await callback.message.edit_text("🏠 Головне меню:", reply_markup=None)
    await callback.message.answer("🏠 Головне меню:", reply_markup=get_main_menu(is_admin=isadm))

# --- Обробка callback для копіювання номера телефону ---
@dp.callback_query(lambda c: c.data == "copy_phone")
async def copy_phone_callback(callback: CallbackQuery):
    logger.info(f"📋 Копіювання номера телефону від користувача {callback.from_user.id}")
    await callback.answer("Номер скопійовано!", show_alert=True)
    await callback.message.answer("+380681234345")

# --- Загальний обробник для логування всіх повідомлень ---
@dp.message()
async def log_all_messages(message: Message):
    """Логує всі необроблені повідомлення"""
    logger.warning(f"⚠️ Необроблене повідомлення від {message.from_user.id}: text='{message.text}', content_type={message.content_type}")

# --- Health Check ---
async def health_check(request):
    """Health check endpoint для Koyeb"""
    return web.Response(text="OK", status=200)

# --- Keep-Alive функція ---
async def keep_alive_ping():
    """Періодичний ping щоб сервер не засинав"""
    if WEBHOOK_HOST:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{WEBHOOK_HOST}/health") as resp:
                    if resp.status == 200:
                        logger.debug("✅ Keep-alive ping successful")
                    else:
                        logger.warning(f"⚠️ Keep-alive ping returned status {resp.status}")
        except Exception as e:
            logger.error(f"❌ Keep-alive ping failed: {e}")

async def on_startup(app):
    """Викликається при запуску"""
    logger.info("Запуск бота в режимі webhook...")
    logger.info(f"WEBHOOK_HOST: {WEBHOOK_HOST}")
    logger.info(f"WEBHOOK_URL: {WEBHOOK_URL}")
    
    # Реєструємо обробники
    register_broadcast_handlers(dp, bot, get_main_menu)
    start_scheduler(bot)
    
    # Запускаємо keep-alive scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(keep_alive_ping, 'interval', minutes=5)  # Ping кожні 5 хвилин
    scheduler.start()
    logger.info("🔄 Keep-alive scheduler запущено (ping кожні 5 хвилин)")
    
    # Встановлюємо webhook
    if WEBHOOK_HOST:
        try:
            await bot.set_webhook(
                url=WEBHOOK_URL,
                drop_pending_updates=True
            )
            logger.info(f"✅ Webhook встановлено: {WEBHOOK_URL}")
            
            # Перевіряємо статус webhook
            webhook_info = await bot.get_webhook_info()
            logger.info(f"📊 Webhook info: url={webhook_info.url}, pending_update_count={webhook_info.pending_update_count}")
            if webhook_info.last_error_message:
                logger.error(f"❌ Останя помилка webhook: {webhook_info.last_error_message}")
        except Exception as e:
            logger.error(f"❌ Помилка встановлення webhook: {e}", exc_info=True)
    else:
        logger.warning("⚠️ WEBHOOK_HOST не встановлено, бот працюватиме без webhook")

async def on_shutdown(app):
    """Викликається при зупинці"""
    logger.info("Зупинка бота...")
    await bot.delete_webhook()
    await bot.session.close()

def main():
    """Головна функція запуску"""
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Запуск веб-сервера на порту {port}")
    
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
    
    # Логування маршрутів
    logger.info("📍 Зареєстровані маршрути:")
    for route in app.router.routes():
        logger.info(f"  {route.method} {route.resource}")
    
    # Запускаємо сервер
    setup_application(app, dp, bot=bot)
    web.run_app(app, host='0.0.0.0', port=port)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"Критична помилка: {e}", exc_info=True)
        sys.exit(1)
