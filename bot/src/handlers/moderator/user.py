import math

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from src.services.user import Users
from src.utils.filters import ModeratorFilter
from src.utils.tools import notify_about_adding

from .deps import Keyboard as K
from .deps import Message as M


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


def router():
    router = Router()
    for func, trigger in (
        (cb_categories, F.data.endswith("~user_categories")),
        (cb_by_status, F.data.endswith("~users")),
        (cb_info, F.data.endswith("~user_info")),
        (cb_change_status, F.data.endswith("~change_status")),

        (cb_user_activation, F.data.endswith("~user_activation")),
    ):
        router.callback_query.register(func, trigger, ModeratorFilter())
    return router