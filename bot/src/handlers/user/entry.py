from datetime import date, datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from src.services.booking import Booking, User
from src.utils.tools import month_alias_dec, notify_admin, set_user_commands

from .deps import Keyboard as K

HI_MESSAGE = (
    "Добро пожаловать!\nС помощью бота можно записаться на массаж, "
    "просмотреть свои записи, при необходимости отменить запись"
)
commands_was_activated = []


async def cmd_start(message: Message):
    global commands_was_activated

    user_id = message.from_user.id
    if user_id not in commands_was_activated:
        is_ok = await set_user_commands(message.bot, user_id)
        if is_ok:
            commands_was_activated.append(user_id)

    appointments = await Booking.user_appointments(user_id)
    free_slots: dict[date, int] = await Booking.get_month_slots_count()
    await message.answer(
        HI_MESSAGE,
        reply_markup=K.menu(len(appointments), free_slots),
    )


async def cb_menu(cb: CallbackQuery):
    await cb.answer()

    user_id = cb.from_user.id
    appointments = await Booking.user_appointments(user_id)

    free_slots: dict[date, int] = await Booking.get_month_slots_count()
    await cb.message.edit_text(
        HI_MESSAGE,
        reply_markup=K.menu(len(appointments), free_slots),
    )


async def cb_empty(cb: CallbackQuery):
    await cb.answer()


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
    await cb.message.edit_text(
        "Записаться можно в часы помечанные зеленым цветом",
        reply_markup=K.day(d, rows),
    )


async def cb_my_appointments(cb: CallbackQuery):
    user_id = cb.from_user.id
    appointments = await Booking.user_appointments(user_id)
    if not appointments:
        await cb.answer("У Вас нет записей", show_alert=True)
        return

    await cb.answer()

    await cb.message.edit_text(
        "Для удаления записи на посещение нажмите на нее",
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

    is_ok = False
    if not session.user.id:
        user = User(id=cb.from_user.id, fullname=cb.from_user.full_name)
        is_ok = await Booking.make_appointment(session.id, user)
        if is_ok:
            await notify_admin(cb.bot, session, user, "make")

    await cb.answer("Вы записались" if is_ok else "Уже заняно", show_alert=True)

    rows = await Booking.get_by_day(session.date)
    await cb.message.edit_text(
        "Записаться можно в часы помечанные зеленым цветом",
        reply_markup=K.day(session.date, rows),
    )


async def cb_delete_my_appointment(cb: CallbackQuery):
    user_id = cb.from_user.id

    session_id, sure_flag, *_ = cb.data.split('~')
    session_id = int(session_id)

    session = await Booking.get(session_id)
    if session:
        if not sure_flag:
            await cb.answer()

            await cb.message.edit_text(
                "Вы действительно хотите отменить запись "
                f"<u>{session.date.day} {month_alias_dec(session.date.month)} на "
                f"{session.time.hour}:00</u>?",
                reply_markup=K.confirm_cancel_appointment(session),
            )
            return

        is_ok = await Booking.reset_appointment(session_id)
        if is_ok:
            await notify_admin(
                cb.bot,
                session,
                User(id=user_id, fullname=cb.from_user.full_name),
                "reject",
            )

        await cb.answer("Запись отменена!")
    else:
        await cb.answer()

    appointments = await Booking.user_appointments(user_id)
    if not appointments:
        free_slots: dict[date, int] = await Booking.get_month_slots_count()
        text = HI_MESSAGE
        rpm = K.menu(len(appointments), free_slots)
    else:
        text = "Для удаления записи на посещение нажмите на нее"
        rpm = K.appointments(appointments)

    await cb.message.edit_text(text, reply_markup=rpm)


def router():
    router = Router()

    router.message.register(cmd_start, Command('run'))

    for handler, filter in (
        (cb_menu, F.data.endswith("~user_menu")),
        (cb_empty, F.data.endswith("~empty")),
        (cb_my_appointments, F.data.endswith("~my_appointment")),
        (cb_explore_month, F.data.endswith("~explore_month")),
        (cb_explore_day, F.data.endswith("~explore_day")),
        (cb_make_appointment, F.data.endswith("~make_appointment")),
        (cb_delete_my_appointment, F.data.endswith("~delete_my_appointment")),
    ):
        router.callback_query.register(handler, filter)

    return router
