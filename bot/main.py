import asyncio
import logging

import aiocron
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from src.config import config
from src.handlers import attach_handlers
from src.services.booking import Booking
from src.utils.tools import startup

logging.basicConfig(level="INFO",
                    format="%(asctime)s [%(levelname)s]: %(name)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(__name__)

async def main():
    await Booking.init_db()

    bot = Bot(token=config.token,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    @aiocron.crontab("0 */1 * * *")
    async def job_1_remove_past_rows():
        pass

    dp = Dispatcher()
    dp.startup.register(startup)

    attach_handlers(dp)

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    except Exception:
        logger.exception("pooling down")
    else:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
