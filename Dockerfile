FROM python:3.11-slim

WORKDIR /app

# Копіюємо файли залежностей
COPY requirements.txt .

# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо всі файли проекту
COPY . .

# Встановлюємо порт
EXPOSE 8000

# Запускаємо бота
CMD ["python", "bot.py"]
