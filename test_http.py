#!/usr/bin/env python3
"""
Тест HTTP health check сервера
"""
import asyncio
from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="OK", status=200)

async def start_web_server(port: int):
    """Запуск веб-сервера"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ HTTP сервер запущено на http://0.0.0.0:{port}")
    logger.info(f"   Перевірте: http://localhost:{port}/health")
    
    # Тримаємо сервер активним
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Зупинка сервера...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    port = 8000
    print(f"Запуск тестового HTTP сервера на порту {port}...")
    print(f"Натисніть Ctrl+C для зупинки\n")
    asyncio.run(start_web_server(port))
