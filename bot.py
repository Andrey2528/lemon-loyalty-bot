from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, Contact, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.client.default import DefaultBotProperties
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

# --- HTTP Health Check Endpoint ---
async def health_check(request):
    """Health check endpoint для Koyeb"""
    return web.Response(text="OK", status=200)

async def start_web_server(port: int):
    """Запуск веб-сервера для health check"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"HTTP сервер запущено на порту {port}")
    return runner

async def main():
    logger.info("Бот запускається...")
    port = int(os.getenv("PORT", 8000))
    
    # Запускаємо HTTP сервер для health check
    runner = await start_web_server(port)
    
    max_retries = 5
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Спроба підключення {attempt + 1}/{max_retries}")
            register_broadcast_handlers(dp, bot, get_main_menu)
            start_scheduler(bot)
            
            # Тест підключення до Telegram з кастомним timeout
            logger.info("Тестування підключення до Telegram API...")
            me = await asyncio.wait_for(bot.get_me(), timeout=30.0)
            logger.info(f"Бот успішно підключений: @{me.username}")
            logger.info("Бот готовий до роботи")
            
            await dp.start_polling(bot, polling_timeout=20, request_timeout=30)
            break
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout при підключенні (спроба {attempt + 1})")
            if attempt < max_retries - 1:
                logger.info(f"Повторна спроба через {retry_delay} секунд...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 60)  # Збільшуємо затримку, але не більше 60 сек
            else:
                logger.error("Всі спроби підключення невдалі через timeout")
                raise
        except Exception as e:
            logger.error(f"Помилка при запуску бота (спроба {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Повторна спроба через {retry_delay} секунд...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 60)
            else:
                logger.error("Всі спроби підключення невдалі")
                raise
    
    # Cleanup
    await runner.cleanup()

if __name__ == "__main__":
    logger.info(f"Запуск бота...")
    
    # Встановлюємо глобальний timeout для asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"Критична помилка: {e}")
        sys.exit(1)