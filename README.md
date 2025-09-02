# Lemon Loyalty Bot

Telegram бот системи лояльності для ресторану Lemon з підтримкою Supabase PostgreSQL.

## Особливості

- 📱 QR-коди для нарахування бонусів
- 💰 Система накопичення балів
- 🍽 Інтеграція з меню закладу
- 🛵 Доставка через Bolt Food
- 📅 Бронювання столиків
- 🏷 Управління акціями
- ⚙️ Адмін-панель для розсилок

## Деплой на Koyeb + Supabase

### Підготовка
1. Створіть акаунт на [Koyeb](https://www.koyeb.com/)
2. Створіть акаунт на [Supabase](https://supabase.com/) для бази даних
3. Підключіть ваш GitHub репозиторій

### Налаштування Supabase
1. **Створіть новий проект** в Supabase
2. **Скопіюйте Database URL:**
   - Перейдіть в Settings → Database
   - Скопіюйте Connection string (URI format)
   - Формат: `postgresql://[user]:[password]@[host]:[port]/[database]`

### Кроки деплою

1. **Увійдіть в Koyeb та створіть новий сервіс:**
   - Клікніть "Create App"
   - Виберіть "Deploy from Git"
   - Підключіть GitHub та виберіть репозиторій

2. **Налаштування сервісу:**
   - **Name**: `lemon-loyalty-bot`
   - **Type**: Web Service
   - **Instance type**: Nano (безкоштовно)
   - **Regions**: Frankfurt

3. **Налаштування сборки:**
   - **Builder**: Buildpack
   - **Build command**: `pip install -r requirements.txt`
   - **Run command**: `python bot.py`

4. **Змінні середовища:**
   - `TELEGRAM_TOKEN` = ваш токен бота (отримайте у @BotFather)
   - `DATABASE_URL` = PostgreSQL URL з Supabase

⚠️ **ВАЖЛИВО**: Ніколи не зберігайте токени в коді! Використовуйте тільки змінні середовища.

5. **Деплой:**
   - Клікніть "Deploy"
   - Очікайте завершення сборки

### Переваги Koyeb + Supabase

- 🆓 **Безкоштовно**: 512MB RAM на Koyeb + 2GB DB на Supabase
- 🔄 **Автореstart** при збоях
- 📊 **Моніторинг** в реальному часі
- 🗄️ **Постійна база даних** - дані не втрачаються при restart
- 🌍 **Global CDN**
- 🔒 **Автоматичний HTTPS**

## Локальний запуск

1. **Встановіть залежності:**
```bash
pip install -r requirements.txt
```

2. **Створіть .env файл:**
```bash
cp .env.example .env
# Заповніть TELEGRAM_TOKEN та DATABASE_URL
```

3. **Запустіть бота:**
```bash
python bot.py
```

## Структура проекту

- `bot.py` - основний файл бота
- `config.py` - конфігурація та змінні середовища  
- `db.py` - робота з базою даних (Supabase/SQLite)
- `broadcast.py` - розсилка повідомлень та адмін-функції
- `.koyeb.yml` - конфігурація для Koyeb
- `Dockerfile` - контейнеризація
- `start.bat` - локальний запуск в Windows

## База даних

Бот автоматично визначає тип бази даних:
- **Production**: PostgreSQL через Supabase (якщо є DATABASE_URL)
- **Development**: SQLite локально (fallback)

Таблиці створюються автоматично при першому запуску.
