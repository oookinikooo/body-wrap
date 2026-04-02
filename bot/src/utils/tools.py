import asyncio
import logging
from typing import Literal

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat
from src.config import config
from src.services.booking import Session, User

logger = logging.getLogger('utils.tools')


def month_alias(pos: int) -> str:
    '''Get name of month by pos. Pos may be number between 1-12'''
    return (
        "Январь", "Февраль", "Март", "Апрель",
        "Май", "Июнь", "Июль", "Август",
        "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    )[pos - 1]


def month_alias_dec(pos: int) -> str:
    '''Get declansion name of month by pos. Pos may be number between 1-12'''
    return (
        "Января", "Февраля", "Марта", "Апреля",
        "Мая", "Июня", "Июля", "Августа",
        "Сентября", "Октября", "Ноября", "Декабря",
    )[pos - 1]


def weekday_alias(pos: int) -> str:
    return ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")[pos]


async def set_commands(bot: Bot, chat_id: int, commands: list[BotCommand]):
    try:
        is_ok = await bot.set_my_commands(
            commands,
            scope=BotCommandScopeChat(chat_id=chat_id),
        )
    except Exception as e:
        logger.error(f"Set commands for user #{chat_id} failed\n"
                     f"{type(e).__name__}: {e}")
    else:
        return is_ok
    return False


async def set_user_commands(bot: Bot, user_id: int):
    return await set_commands(
        bot,
        user_id,
        [BotCommand(command="run", description="Открыть меню")],
    )


async def set_moderator_commands(bot: Bot, user_id: int):
    return await set_commands(
        bot,
        user_id,
        [
            BotCommand(command="start", description="Открыть меню"),
            BotCommand(command="restart", description="Перезапуск"),
        ],
    )


async def startup(bot: Bot):
    await bot.send_message(chat_id=config.admin_ids[0], text='Bot started')


async def notify_admin(
    bot: Bot,
    session: Session,
    user: User,
    action: Literal["make", "reject"],
) -> bool:
    profile_link = f'<a href="tg://user?id={user.id}">{user.fullname}</a>'
    text = (
        f"{'✅ Записался' if action == 'make' else '❌ Отменил'} "
        f"{profile_link} {session.date.day} {month_alias_dec(session.date.month)} "
        f"{weekday_alias(session.date.weekday())} на {session.time.hour}:00"
    )
    for i in (1, 2, 3):
        for admin_id in config.admin_ids:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Notify failed. Attempt-{i}. Retry after 0.15s\n"
                            f"{type(e).__name__}: {e}")
                await asyncio.sleep(0.15)
            else:
                break

    return True
