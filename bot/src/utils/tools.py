import asyncio
import logging
from datetime import datetime
from typing import Literal

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, InlineKeyboardMarkup
from aiogram.types import InlineKeyboardButton as Button
from src.config import config
from src.services.booking import Booking, Session
from src.services.user import User, Users

logger = logging.getLogger('utils.tools')


def month_alias(pos: int) -> str:
    '''Get name of month by pos. Pos may be number between 1-12'''
    return (
        "январь", "февраль", "март", "апрель",
        "май", "июнь", "июль", "август",
        "сентябрь", "октябрь", "ноябрь", "декабрь"
    )[pos - 1]


def month_alias_dec(pos: int) -> str:
    '''Get declansion name of month by pos. Pos may be number between 1-12'''
    return (
        "января", "февраля", "марта", "апреля",
        "мая", "июня", "июля", "августа",
        "сентября", "октября", "ноября", "декабря",
    )[pos - 1]


def weekday_alias(pos: int) -> str:
    return ("пн", "вт", "ср", "чт", "пт", "сб", "вс")[pos]


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
        [BotCommand(command="start", description="Открыть меню")],
    )


async def set_moderator_commands(bot: Bot, user_id: int):
    return await set_commands(
        bot,
        user_id,
        [
            BotCommand(command="start", description="Открыть меню"),
            BotCommand(command="send", description="Отправить сообщение пользователям"),
            BotCommand(command="restart", description="Перезапуск"),
        ],
    )


async def startup(bot: Bot):
    await bot.send_message(chat_id=config.admin_ids[0], text='Bot started')


async def notify_admin(bot: Bot, session: Session, action: Literal["make", "reject"]) -> bool:
    user = session.user
    if not user:
        logger.error(f"Notify admin about {action} session #{session.id} failed")
        return False

    profile_link = f'<a href="tg://user?id={user.id}">{user.fullname}</a>'
    text = (
        f"{'✅ Записался' if action == 'make' else '❌ Отменил'} {profile_link} "
        f"{session.date.day} {month_alias_dec(session.date.month)} "
        f"{weekday_alias(session.date.weekday())} на {session.time.hour}:00"
    )
    for admin_id in config.admin_ids:
        for i in (1, 2, 3):
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Notify failed. Attempt-{i}. Retry after 0.15s\n"
                            f"{type(e).__name__}: {e}")
                await asyncio.sleep(0.15)
            else:
                break

    return True


async def notify_users_about_freed_slot(
    bot: Bot,
    session: Session,
    ignore_ids: list[int] | None = None,
):
    now = datetime.today()
    if session.date.year == now.year and session.date.month == now.month:
        month_slots = await Booking.get_month_slots_count()
        if free_slots := month_slots.get(now.date().replace(day=1)):
            if 0 < free_slots <= 3:
                text = (
                    f"{session.date.day} {month_alias_dec(session.date.month)} "
                    f"на {session.time.hour:02}:{session.time.minute:02} освободилось время на массаж"
                )
                if ignore_ids is None:
                    ignore_ids = []

                position, page, cap = 0, 0, 10
                while True:
                    users = await Users().get_slice(page, cap, is_active=True)
                    if not users:
                        break

                    page += 1

                    for user in users:
                        if user.id in ignore_ids:
                            continue

                        if position != 0 and position % cap == 0:
                            await asyncio.sleep(0.15)

                        position += 1

                        try:
                            await bot.send_message(chat_id=user.id, text=text, parse_mode=None)
                        except Exception as e:
                            logger.error(f"Send manager msg to #{user.id} - {e}")
                            await asyncio.sleep(0.075)


def hi():
    now_hour = datetime.now().hour
    if now_hour < 12:
        hi = "Доброе утро"
    elif now_hour > 18:
        hi = "Добрый вечер"
    else:
        hi = "Привет"
    return hi


async def notify_user(
    bot: Bot,
    user_id: int,
    sessions: list[Session],
    when: Literal["today", "tomorrow"] = "today",
) -> bool:
    if hours := sorted([s.time.hour for s in sessions if s.user]):
        hours_list = ', '.join([f'{h}:00' for h in hours])
        text = (
            f"{hi()}!\nНапоминаю, "
            f"{'сегодня' if when == 'today' else 'завтра'} "
            f"в {hours_list} вы записаны на обертывание"
        )
        for i in (1, 2, 3):
            try:
                await bot.send_message(user_id, text)
            except Exception as e:
                logger.error(f"Notify user failed. Attempt-{i}. Retry after 0.15s\n"
                            f"{type(e).__name__}: {e}")
                await asyncio.sleep(0.15)
            else:
                return True
    return False


async def notify_about_adding(bot: Bot, user_id: int):
    text = "✅ Доступ предоставлен\nНажмите комманду /start для начала работы"
    for i in (1, 2, 3):
        try:
            await bot.send_message(user_id, text)
        except Exception as e:
            logger.error(f"Notify user about adding failed. Attempt-{i}. "
                         f"Retry after 0.15s\n{type(e).__name__}: {e}")
            await asyncio.sleep(0.15)
        else:
            await set_user_commands(bot, user_id)
            return True
    return False


async def notify_admin_about_new_user(bot: Bot, user: User):
    text = f"☘️ Новый пользователь #{user.id} - {user.fullname}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            Button(text="Добавить", callback_data=f"1~{user.id}~user_activation"),
            Button(text="Отклонить", callback_data=f"~{user.id}~user_activation"),
        ]
    ]) 
    for admin_id in config.admin_ids:
        for i in (1, 2, 3):
            try:
                await bot.send_message(
                    admin_id,
                    text,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(
                    f"Notify admin about new user failed. Attempt-{i}. "
                    f"Retry after 0.15s\n{type(e).__name__}: {e}"
                )
                await asyncio.sleep(0.15)
            else:
                break
    return True