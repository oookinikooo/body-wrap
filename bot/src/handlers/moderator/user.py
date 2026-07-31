import asyncio
import logging
import math

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from src.services.user import Users
from src.utils.filters import ModeratorFilter
from src.utils.tools import notify_about_adding

from .deps import Keyboard as K
from .deps import Message as M

logger = logging.getLogger(__name__)


async def cb_categories(cb: CallbackQuery):
    await cb.answer()

    count = await Users().count()
    await cb.message.edit_text(
        f"Всего пользователей - {count}",
        reply_markup=K.user.categories(),
    )


async def cb_by_status(cb: CallbackQuery):
    await cb.answer()

    page, flag, *_ = cb.data.split("~")
    page, cap = int(page), 10
    flag = bool(int(flag))

    mark = "с доступом" if flag else "без доступа"

    count = await Users().count(flag)
    if count == 0:
        await cb.message.edit_text(
            f'Нет пользователей в категории "{mark}"',
            reply_markup=K.user.go_back(),
        )
    else:
        total_page = math.ceil(count / cap)
        rows = await Users().get_slice(page, cap, bool(flag))
        await cb.message.edit_text(
            f"({page + 1} / {total_page}) Пользователей {mark} - {count}",
            reply_markup=K.user.slider(rows, page, total_page),
        )


async def cb_info(cb: CallbackQuery):
    user_id, page, *_ = cb.data.split("~")
    user = await Users().get(int(user_id))
    if not user:
        await cb.answer("Пользователь не найден", show_alert=True)
        return

    await cb.answer()

    await cb.message.edit_text(
        M.user.info(user),
        reply_markup=K.user.action(user, page, user.is_active),
    )


async def cb_change_status(cb: CallbackQuery, bot: Bot):
    await cb.answer()

    user_id, page, is_active, *_ = cb.data.split("~") 
    user_id = int(user_id)
    user = await Users().get(user_id)
    if not user:
        return

    is_ok = await Users().set_is_active(user_id, not user.is_active)
    if is_ok:
        user.is_active = not user.is_active
        if user.is_active:
            await notify_about_adding(bot, user_id)

    from_rows = True if is_active == "1" else False
    try:
        await cb.message.edit_text(
            text=M.user.info(user),
            reply_markup=K.user.action(user, page, from_rows)
        )
    except Exception as e:
        print(e)


async def cb_user_activation(cb: CallbackQuery, bot: Bot):
    flag, user_id, *_ = cb.data.split("~")

    msg = await cb.message.edit_reply_markup(reply_markup=None)

    user_id = int(user_id)
    if flag:
        is_ok = await Users().set_is_active(user_id, True)
        if is_ok:
            await notify_about_adding(bot, int(user_id))
            text = "Добавлен и уведомление пользователю отправлено"
        else:
            text = (
                "Ошибка добавления, воспользуйтесь кнопкой "
                "Пользователи и активируйте пользователя там"
            )
    else:
        text = "Не добавлен"
    await msg.reply(text)


async def cmd_send(message: Message, bot: Bot):
    reply_to_message = message.reply_to_message
    if reply_to_message is None:
        text = (
            "Отправка сообщения пользователям бота\n\n"
            "Введите комманду /send ссылаясь на то сообщение из текущего чата, "
            "которым хотите поделиться\n\n"
            "<i>Примечание: текст сообщения будет отправлен в том виде, "
            "в котором вы его написали, учитывая форматирование и стикеры</i>"
        )
        await message.answer(text)
        return

    text, entities = reply_to_message.text, reply_to_message.entities
    if not text:
        await message.answer("Вы ссылаетесь на сообщение в котором нет текста")
        return

    total = await Users().count(is_active=True)
    progress_text = "Отправлено {} из {}".format('{}', total)

    msg = await message.answer(progress_text.format(0))

    position, page, cap = 0, 0, 10
    while True:
        users = await Users().get_slice(page, cap, is_active=True)
        if not users:
            break

        page += 1

        for user in users:
            if position != 0 and position % cap == 0:
                await msg.edit_text(progress_text.format(position)) 
                await asyncio.sleep(0.5)

            position += 1

            for _ in (0, 1):
                try:
                    await bot.send_message(
                        chat_id=user.id,
                        text=text,
                        entities=entities,
                        parse_mode=None,
                    )
                    break
                except Exception as e:
                    logger.error(f"Send manager msg to #{user.id} - {e}")
                    if "bot was blocked by the user" in str(e):
                        break

                    await asyncio.sleep(0.15)

    await msg.edit_text(f"Отправлено {position} из {total}")


def router():
    router = Router()
    for func, cmd_filter in (
        (cmd_send, Command("send")),
    ):
        router.message.register(func, cmd_filter, ModeratorFilter())
    for func, trigger in (
        (cb_categories, F.data.endswith("~user_categories")),
        (cb_by_status, F.data.endswith("~users")),
        (cb_info, F.data.endswith("~user_info")),
        (cb_change_status, F.data.endswith("~change_status")),

        (cb_user_activation, F.data.endswith("~user_activation")),
    ):
        router.callback_query.register(func, trigger, ModeratorFilter())
    return router