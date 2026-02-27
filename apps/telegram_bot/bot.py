"""Точка входа Parts Assistant Telegram Bot."""
from __future__ import annotations

import asyncio
import logging
import os
import sys

# Добавить в PYTHONPATH директорию с app и core (core-api) и apps
# В dev: project_root/services/core-api; в Docker: /app (уже содержит app, core, apps)
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_core_api = os.path.join(_root, "services", "core-api")
if os.path.isdir(_core_api):
    sys.path.insert(0, _core_api)
if _root not in sys.path:
    sys.path.insert(0, _root)

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .handlers import commands, messages, callbacks

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        sys.exit(1)

    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(commands.router)
    dp.include_router(messages.router)
    dp.include_router(callbacks.router)

    logger.info("Telegram bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
