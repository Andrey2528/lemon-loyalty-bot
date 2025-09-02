from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_USERNAMES
import db
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

def is_admin(message: Message):
    return message.from_user.username in ADMIN_USERNAMES

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_weekly_text = State()
    waiting_for_weekly_send = State()
    waiting_for_time = State()
    waiting_for_promo_action = State()
    waiting_for_new_promo = State()
    waiting_for_edit_promo_id = State()
    waiting_for_edit_promo_text = State()
    waiting_for_delete_promo_id = State()

# --- FSM та хендлери для розсилок та адмін-панелі ---
def register_broadcast_handlers(dp, bot, get_main_menu):
    @dp.message(lambda m: m.text == "⚙️ Адмін-панель")
    async def admin_panel(message: Message):
        if not is_admin(message):
            return await message.answer("⛔️ Доступ заборонено.")
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📢 Одноразова розсилка")],
                [KeyboardButton(text="🔁 Тижнева розсилка")],
                [KeyboardButton(text="✏️ Редагувати текст тижневої розсилки")],
                [KeyboardButton(text="⏰ Редагувати час тижневої розсилки")],
                [KeyboardButton(text="📝 Редагувати акції")],
                [KeyboardButton(text="‹ Повернутись до меню")],
            ], resize_keyboard=True
        )
        await message.answer("Адмін-панель:", reply_markup=kb)

    @dp.message(lambda m: m.text == "⏰ Редагувати час тижневої розсилки")
    async def edit_weekly_time(message: Message, state: FSMContext):
        if not is_admin(message):
            return await message.answer("⛔️ Доступ заборонено.")
        days_hint = (
            "0 = неділя\n"
            "1 = понеділок\n"
            "2 = вівторок\n"
            "3 = середа\n"
            "4 = четвер\n"
            "5 = п'ятниця\n"
            "6 = субота"
        )
        await message.answer(
            f"Введіть новий час у форматі: день_тижня година:хвилина\nНаприклад: 5 18:00\n\nДні тижня:\n{days_hint}"
        )
        await state.set_state(AdminStates.waiting_for_time)

    @dp.message(AdminStates.waiting_for_time)
    async def save_weekly_time(message: Message, state: FSMContext):
        try:
            parts = message.text.strip().split()
            day = int(parts[0])
            hour, minute = map(int, parts[1].split(":"))
            db.set_weekly_time(day, hour, minute)
            await message.answer(f"Час тижневої розсилки збережено: {day} {hour:02d}:{minute:02d}", reply_markup=get_main_menu(is_admin=is_admin(message)))
            await state.clear()
        except Exception:
            await message.answer("Невірний формат. Спробуйте ще раз: день_тижня година:хвилина")

    @dp.message(lambda m: m.text == "📢 Одноразова розсилка")
    async def once_broadcast(message: Message, state: FSMContext):
        if not is_admin(message):
            return await message.answer("⛔️ Доступ заборонено.")
        await message.answer("Введіть текст для одноразової розсилки:")
        await state.set_state(AdminStates.waiting_for_broadcast)

    @dp.message(AdminStates.waiting_for_broadcast)
    async def send_once_broadcast(message: Message, state: FSMContext):
        users = db.get_all_users()
        sent = 0
        failed = 0
        for user in users:
            try:
                await bot.send_message(user[0], message.text)
                sent += 1
            except Exception:
                failed += 1
        await message.answer(f"Розсилку надіслано. Успішно: {sent}, помилок: {failed}.", reply_markup=get_main_menu(is_admin=is_admin(message)))
        await state.clear()

    @dp.message(lambda m: m.text == "🔁 Тижнева розсилка")
    async def weekly_broadcast(message: Message):
        if not is_admin(message):
            return await message.answer("⛔️ Доступ заборонено.")
        text = db.get_weekly_broadcast() or "Текст тижневої розсилки ще не задано."
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Надіслати тижневу розсилку")], [KeyboardButton(text="‹ Повернутись до меню")]],
            resize_keyboard=True
        )
        await message.answer(f"Поточний текст тижневої розсилки:\n\n{text}", reply_markup=kb)

    @dp.message(lambda m: m.text == "✅ Надіслати тижневу розсилку")
    async def send_weekly_broadcast(message: Message):
        if not is_admin(message):
            return await message.answer("⛔️ Доступ заборонено.")
        text = db.get_weekly_broadcast()
        if not text:
            return await message.answer("Текст тижневої розсилки не задано.")
        users = db.get_all_users()
        sent = 0
        failed = 0
        for user in users:
            try:
                await bot.send_message(user[0], text)
                sent += 1
            except Exception:
                failed += 1
        await message.answer(f"Тижнева розсилка надіслана. Успішно: {sent}, помилок: {failed}.", reply_markup=get_main_menu(is_admin=is_admin(message)))

    @dp.message(lambda m: m.text == "✏️ Редагувати текст тижневої розсилки")
    async def edit_weekly_broadcast(message: Message, state: FSMContext):
        if not is_admin(message):
            return await message.answer("⛔️ Доступ заборонено.")
        await message.answer("Введіть новий текст для тижневої розсилки:")
        await state.set_state(AdminStates.waiting_for_weekly_text)

    @dp.message(AdminStates.waiting_for_weekly_text)
    async def save_weekly_broadcast(message: Message, state: FSMContext):
        db.set_weekly_broadcast(message.text)
        await message.answer("Текст тижневої розсилки збережено!", reply_markup=get_main_menu(is_admin=is_admin(message)))
        await state.clear()
        
    # --- Редагування акцій ---
    @dp.message(lambda m: m.text == "📝 Редагувати акції")
    async def promo_action_menu(message: Message, state: FSMContext):
        if not is_admin(message):
            return await message.answer("⛔️ Доступ заборонено.")
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Додати акцію")],
                [KeyboardButton(text="✏️ Редагувати акцію")],
                [KeyboardButton(text="❌ Видалити акцію")],
                [KeyboardButton(text="‹ Повернутись до меню")],
            ], resize_keyboard=True
        )
        await message.answer("Оберіть дію з акціями:", reply_markup=kb)
        await state.set_state(AdminStates.waiting_for_promo_action)

    @dp.message(AdminStates.waiting_for_promo_action)
    async def handle_promo_action(message: Message, state: FSMContext):
        if message.text == "➕ Додати акцію":
            await message.answer("Введіть текст нової акції:")
            await state.set_state(AdminStates.waiting_for_new_promo)
        elif message.text == "✏️ Редагувати акцію":
            promos = db.get_promos()
            if not promos:
                await message.answer("Немає акцій для редагування.", reply_markup=get_main_menu(is_admin=is_admin(message)))
                await state.clear()
                return
            text = "Введіть номер акції для редагування:\n"
            for pid, promo in promos:
                text += f"{pid}. {promo}\n"
            await message.answer(text)
            await state.set_state(AdminStates.waiting_for_edit_promo_id)
        elif message.text == "❌ Видалити акцію":
            promos = db.get_promos()
            if not promos:
                await message.answer("Немає акцій для видалення.", reply_markup=get_main_menu(is_admin=is_admin(message)))
                await state.clear()
                return
            text = "Введіть номер акції для видалення:\n"
            for pid, promo in promos:
                text += f"{pid}. {promo}\n"
            await message.answer(text)
            await state.set_state(AdminStates.waiting_for_delete_promo_id)
        elif message.text == "‹ Повернутись до меню":
            await message.answer("Повернення до меню.", reply_markup=get_main_menu(is_admin=is_admin(message)))
            await state.clear()
        else:
            await message.answer("Оберіть дію з меню.")

    @dp.message(AdminStates.waiting_for_new_promo)
    async def add_new_promo(message: Message, state: FSMContext):
        db.add_promo(message.text)
        await message.answer("Акцію додано!", reply_markup=get_main_menu(is_admin=is_admin(message)))
        await state.clear()

    @dp.message(AdminStates.waiting_for_edit_promo_id)
    async def ask_edit_promo_text(message: Message, state: FSMContext):
        try:
            promo_id = int(message.text.strip())
        except Exception:
            await message.answer("Введіть коректний номер акції!")
            return
        promos = db.get_promos()
        if not any(pid == promo_id for pid, _ in promos):
            await message.answer("Акції з таким номером не існує!")
            return
        await state.update_data(edit_promo_id=promo_id)
        await message.answer("Введіть новий текст для акції:")
        await state.set_state(AdminStates.waiting_for_edit_promo_text)

    @dp.message(AdminStates.waiting_for_edit_promo_text)
    async def save_edited_promo(message: Message, state: FSMContext):
        data = await state.get_data()
        promo_id = data.get("edit_promo_id")
        db.update_promo(promo_id, message.text)
        await message.answer("Акцію оновлено!", reply_markup=get_main_menu(is_admin=is_admin(message)))
        await state.clear()

    @dp.message(AdminStates.waiting_for_delete_promo_id)
    async def delete_promo_handler(message: Message, state: FSMContext):
        try:
            promo_id = int(message.text.strip())
        except Exception:
            await message.answer("Введіть коректний номер акції!")
            return
        promos = db.get_promos()
        if not any(pid == promo_id for pid, _ in promos):
            await message.answer("Акції з таким номером не існує!")
            return
        db.delete_promo(promo_id)
        await message.answer("Акцію видалено!", reply_markup=get_main_menu(is_admin=is_admin(message)))
        await state.clear()

# --- Автоматична тижнева розсилка ---
async def scheduled_weekly_broadcast(bot):
    text = db.get_weekly_broadcast()
    if not text:
        return
    users = db.get_all_users()
    for user in users:
        try:
            await bot.send_message(user[0], text)
        except Exception:
            pass

def start_scheduler(bot):
    scheduler = AsyncIOScheduler()
    def job_wrapper():
        asyncio.create_task(scheduled_weekly_broadcast(bot))
    day, hour, minute = db.get_weekly_time()
    scheduler.add_job(job_wrapper, "cron", day_of_week=day, hour=hour, minute=minute)
    scheduler.start()
