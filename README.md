# Lemon Loyalty Bot

Telegram бот системи лояльності для ресторану Lemon.

## Деплой на Koyeb

### Підготовка
1. Створіть акаунт на [Koyeb](https://www.koyeb.com/)
2. Підключіть ваш GitHub репозиторій
3. Завантажте проект на GitHub

### Кроки деплою

1. **Увійдіть в Koyeb та створіть новий сервіс:**
   - Клікніть "Create App"
   - Виберіть "Deploy from Git"
   - Підключіть GitHub та виберіть репозиторій

2. **Налаштування сервісу:**
   - **Name**: `lemon-loyalty-bot`
   - **Type**: Web Service
   - **Instance type**: Nano (безкоштовно)
   - **Regions**: Frankfurt (найближчий до України)

3. **Налаштування сборки:**
   - **Builder**: Buildpack
   - **Build command**: `pip install -r requirements.txt`
   - **Run command**: `python bot.py`

4. **Змінні середовища:**
   - `TELEGRAM_TOKEN` = ваш токен бота

5. **Деплой:**
   - Клікніть "Deploy"
   - Очікайте завершення сборки

### Особливості

- Безкоштовний план: 512MB RAM, 2.5GB storage
- Автоматичний restart при збоях
- HTTPS підтримка
- Логування в реальному часі

### Моніторинг

Перевіряти статус бота можна в Dashboard Koyeb:
- Логи додатку
- Метрики використання ресурсів
- Історія деплоїв

## Локальний запуск

```bash
pip install -r requirements.txt
python bot.py
```

## Структура проекту

- `bot.py` - основний файл бота
- `config.py` - конфігурація
- `db.py` - робота з базою даних
- `broadcast.py` - розсилка повідомлень
- `.koyeb.yml` - конфігурація для Koyeb
- `Dockerfile` - контейнеризація
