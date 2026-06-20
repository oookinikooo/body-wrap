from datetime import date, datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from src.services.booking import Booking, User
from src.utils.tools import notify_admin

from .deps import Keyboard as K
from .deps import Message as M


async def get_menu_text_rpm(user_id: int):
    appointments = await Booking.user_appointments(user_id)
    active_months: list[date] = await Booking.get_active_month()
    free_slots: dict[date, int] = await Booking.get_month_slots_count()
    return M.welcome, K.menu(len(appointments), active_months, free_slots)


async def cmd_start(message: Message):
    user_id = message.from_user.id

    text, rpm = await get_menu_text_rpm(user_id)
    await message.answer(text, reply_markup=rpm)


async def cb_menu(cb: CallbackQuery):
    await cb.answer()

    user_id = cb.from_user.id

    text, rpm = await get_menu_text_rpm(user_id)
    await cb.message.edit_text(text, reply_markup=rpm)


async def cb_empty(cb: CallbackQuery):
    await cb.answer()


async def cb_no_free_slots(cb: CallbackQuery):
    await cb.answer("Нет мест для записи", show_alert=True)


async def cb_explore_month(cb: CallbackQuery):
    await cb.answer()

    date_str, *_ = cb.data.split('~')
    d = date.fromisoformat(date_str)

    rows = await Booking.get_month_by_date(d)
    await cb.message.edit_text(
        "Зеленым помечены дни где есть свободные окошки",
        reply_markup=K.month(d, rows),
    )


async def cb_explore_day(cb: CallbackQuery):
    await cb.answer()

    date_str, *_ = cb.data.split('~')
    d = date.fromisoformat(date_str)

    rows = await Booking.get_by_day(d)
    await cb.message.edit_text(M.pick_hour(d), reply_markup=K.day(d, rows))


async def cb_my_appointments(cb: CallbackQuery):
    user_id = cb.from_user.id
    appointments = await Booking.user_appointments(user_id)
    if not appointments:
        await cb.answer("У Вас нет записей", show_alert=True)
        return

    await cb.answer()

    await cb.message.edit_text(
        "Ваши записи\nДля удаления записи нажмите на нее",
        reply_markup=K.appointments(appointments),
    )


async def cb_make_appointment(cb: CallbackQuery):
    row_id, *_ = cb.data.split('~')

    session = await Booking.get(int(row_id))
    if not session:
        await cb.answer("Выбранный сеанс не найден!", show_alert=True)
        return

    now = datetime.now()
    if session.date < now.date() or session.date == now.date() and session.time < now.time():
        await cb.answer("Данный сеанс уже прошел", show_alert=True)
        return

    if session.user:
        await cb.answer("Уже занято. Выберите другое время", show_alert=True)
    else:
        is_ok = await Booking.make_appointment(
            session.id,
            User(
                id=cb.from_user.id,
                fullname=cb.from_user.full_name,
                reservation_at=datetime.now(),
            ),
        )
        if is_ok and (session := await Booking.get(session.id)):
            await notify_admin(cb.bot, session, "make")

        if is_ok:
            text = "Вы записались"
        else:
            text = "Ошибка записи. Повторите попытку"
        await cb.answer(text, show_alert=True)

    rows = await Booking.get_by_day(session.date)
    await cb.message.edit_text(
        M.pick_hour(session.date),
        reply_markup=K.day(session.date, rows),
    )


async def cb_delete_my_appointment(cb: CallbackQuery):
    user_id = cb.from_user.id

    session_id, sure_flag, *_ = cb.data.split('~')
    session_id = int(session_id)

    session = await Booking.get(session_id)
    if session and session.user:
        if not sure_flag:
            await cb.answer()

            await cb.message.edit_text(
                M.sure_to_decline(session),
                reply_markup=K.confirm_cancel_appointment(session),
            )
            return

        is_ok = await Booking.reset_appointment(session_id)
        if is_ok:
            await notify_admin(cb.bot, session, "reject")

            text = "Запись отменена!"
        else:
            text = "Запись не отменена! Повторите попытку"

        await cb.answer(text)
    else:
        await cb.answer()

    appointments = await Booking.user_appointments(user_id)
    if not appointments:
        text, rpm = await get_menu_text_rpm(user_id)
    else:
        text = "Ваши записи\nДля удаления записи нажмите на нее"
        rpm = K.appointments(appointments)

    await cb.message.edit_text(text, reply_markup=rpm)


def router():
    router = Router()

    router.message.register(cmd_start, Command('start'))

    for handler, filter in (
        (cb_menu, F.data.endswith("~user_menu")),
        (cb_empty, F.data.endswith("~empty")),
        (cb_no_free_slots, F.data.endswith("~no_free_slots")),
        (cb_my_appointments, F.data.endswith("~my_appointment")),
        (cb_explore_month, F.data.endswith("~explore_month")),
        (cb_explore_day, F.data.endswith("~explore_day")),
        (cb_make_appointment, F.data.endswith("~make_appointment")),
        (cb_delete_my_appointment, F.data.endswith("~delete_my_appointment")),
    ):
        router.callback_query.register(handler, filter)

    return router
