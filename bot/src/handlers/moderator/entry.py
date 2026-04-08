import calendar
import logging
from collections import defaultdict
from datetime import date, datetime, time

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from src.config import config
from src.services.booking import Booking, Session, SessionAdd
from src.utils.filters import ModeratorFilter
from src.utils.tools import (month_alias, month_alias_dec,
                             set_moderator_commands, weekday_alias)

from .desp import Keyboard as K
from .desp import Message as M

logger = logging.getLogger(__name__)
commands_was_activated = []


async def cmd_start(message: Message):
    if await Booking.is_hiden():
        return

    global commands_was_activated

    user_id = message.from_user.id
    if user_id not in commands_was_activated:
        is_ok = await set_moderator_commands(message.bot, user_id)
        if is_ok:
            commands_was_activated.append(user_id)

    await message.answer(M.menu(), reply_markup=K.menu())


async def cb_menu(cb: CallbackQuery):
    await cb.answer()

    await cb.message.edit_text(M.menu(), reply_markup=K.menu())


async def cb_edit_or_add_months(cb: CallbackQuery):
    await cb.answer()

    exists = await Booking.get_active_month()

    await cb.message.edit_text(
        "Для внесения правок в расписание кликните на название месяца",
        reply_markup=K.edit_or_add_months(exists),
    )


async def cb_add_new_month(cb: CallbackQuery):
    open_monhts = await Booking.get_active_month()
    if len(open_monhts) >= 6:
        await cb.answer(
            "Возможно добавление только на 6 месяцев вперед!",
            show_alert=True,
        )
        return

    await cb.answer()

    date = await Booking.open_new_month()

    rows = await Booking.get_month_by_date(date)

    await cb.message.edit_text(
        f"Вы добавили {month_alias(date.month)} месяц, нажимая на дату, "
        "добавьте рабочие часы",
        reply_markup=K.edit_month(date, rows),
    )


async def cb_edit_month(cb: CallbackQuery):
    await cb.answer()

    date_str, *_ = cb.data.split("~")
    parsed_date = date.fromisoformat(date_str)

    rows = await Booking.get_month_by_date(parsed_date)

    await cb.message.edit_text(
        "Проваливайтесь в даты и правьте рабочие часы\n"
        "Неактивные дни помечены синим цветом",
        reply_markup=K.edit_month(parsed_date, rows),
    )


async def cb_edit_day(cb: CallbackQuery):
    await cb.answer()

    date_str, *_ = cb.data.split("~")
    picked_date = date.fromisoformat(date_str)

    rows = await Booking.get_by_day(picked_date)
    await cb.message.edit_text(
        text=M.edit_time(picked_date),
        reply_markup=K.edit_day(picked_date, rows),
    )


async def cb_edit_times(cb: CallbackQuery):
    await cb.answer()

    date_str, hour, row_id, *_ = cb.data.split("~")
    picked_date = date.fromisoformat(date_str)

    row_id = int(row_id) if row_id and row_id != "0" else None
    if row_id:
        session = await Booking.get(row_id)
        if session and session.user:
            await cb.bot.send_message(session.user.id, M.session_rejected(session))
        is_ok = await Booking.delete(row_id)
    else:
        slot = SessionAdd(date=picked_date, time=time(int(hour)))
        exists = await Booking.slot_already_allocated(slot)
        if not exists:
            await Booking.add(slot)

    rows = await Booking.get_by_day(picked_date)
    try:
        await cb.message.edit_text(
            text=M.edit_time(picked_date),
            reply_markup=K.edit_day(picked_date, rows),
        )
    except Exception as e:
        logger.error(f"Edit times for {date_str}\n{type(e).__name__}: {e}")


async def cb_schedule_months(cb: CallbackQuery):
    exists_month = await Booking.get_active_month()
    if not exists_month:
        await cb.answer("Расписания отсутствует", show_alert=True)
        return

    await cb.answer()

    await cb.message.edit_text(
        "Расписание по месяцам",
        reply_markup=K.schedule_months(exists_month),
    )


async def cb_my_schedule(cb: CallbackQuery):
    await cb.answer()

    date_str, page, *_ = cb.data.split("~")
    picked_date = date.fromisoformat(date_str)
    page = int(page) if page and page.isdigit() else 0

    now = datetime.now()
    month_by_week = calendar.monthcalendar(picked_date.year, picked_date.month)
    if picked_date.year == now.year and picked_date.month == now.month:
        new_month_by_week = []
        for row in month_by_week:
            have_row = []
            for d in row:
                if d < now.day:
                    continue
                have_row.append(d)
            if have_row:
                new_month_by_week.append(have_row)
        month_by_week = new_month_by_week

    sessions = await Booking.get_month_by_date(picked_date)

    week_days = month_by_week[page]
    current_week = defaultdict(list[Session])
    for s in sessions:
        if s.date.day in week_days and s.time.hour != 0:
            if s.date == now.date() and s.time < now.time():
                continue
            current_week[s.date.weekday()].append(s)

    msg = (
        f"Расписание c {min(w for w in week_days if w)} по {max(week_days)} "
        f"<b>{month_alias_dec(picked_date.month)}</b>"
    )
    text = ""
    if current_week:
        for week_day_number in sorted(current_week):
            day_sessions = current_week[week_day_number]
            if not day_sessions:
                continue

            text += f"\n\n<u>{day_sessions[0].date:%d.%m} {weekday_alias(week_day_number).lower()}</u>"
            for s in sorted(day_sessions, key=lambda x: x.time):
                if s.user:
                    user_link = f'<a href="tg://user?id={s.user.id}">{s.user.fullname}</a>'
                else:
                    user_link = "Пусто"
                text += f"\n - {s.time.hour}:00 - {user_link}"

    msg += text if text else "\n\nДаты приема отсутствуют"
    await cb.message.edit_text(
        msg,
        reply_markup=K.week_slider(picked_date, page, len(month_by_week)),
    )


async def cb_reset_all(cb: CallbackQuery):
    await cb.answer()

    if await Booking.is_hiden():
        return

    flag, *_ = cb.data.split("~")
    if not flag:
        await cb.message.edit_text(
            "⚠️ Данное действие необратимо. Уверена?",
            reply_markup=K.reset_db(),
        )
        return

    is_ok = False
    for i in (1, 2, 3):
        try:
            await Booking.hide()
        except Exception as e:
            logger.exception(f"Hide db table failed. Attempt {i}")
        else:
            is_ok = True
            logger.info("Hide table success")
            break
    else:
        for i in (1, 2, 3):
            try:
                await Booking.clear_all()
            except Exception as e:
                logging.exception(f"Clear database failed. Attempt {i}")
            else:
                is_ok = True
                logger.info("Clear database, because can't hide table")
                break

    await cb.message.edit_text("Бот временно недоступен")


async def cb_empty(cb: CallbackQuery):
    await cb.answer()


async def cmd_restart(message: Message):
    _, master_str = message.text.split(maxsplit=1)

    if master_str == config.master_key:
        unhide_ok = False
        for i in (1, 2, 3):
            try:
                await Booking.unhide()
            except Exception as e:
                logger.exception(f"Unhide db table failed. Attempt {i}")
            else:
                unhide_ok = True
                logger.info("Unhide table success")
                break

        if unhide_ok:
            text = "Жми /start"
        else:
            text = "Ошибка разблокировки таблицы, обратитесь к администратору"

        await message.answer(text)


def router():
    router = Router()

    for handler, filter in (
        (cmd_start, Command('start')),
        (cmd_restart, Command("restart")),
    ):
        router.message.register(handler, filter, ModeratorFilter())

    for handler, filter in (
        (cb_menu, F.data.endswith("~menu")),
        (cb_edit_or_add_months, F.data.endswith("~edit_schedule")),
        (cb_add_new_month, F.data.endswith("~add_new_month")),
        (cb_edit_month, F.data.endswith("~edit_month")),
        (cb_edit_day, F.data.endswith("~edit_day")),
        (cb_edit_times, F.data.endswith("~edit_time")),

        (cb_schedule_months, F.data.endswith("~schedule_months")),
        (cb_my_schedule, F.data.endswith("~my_schedule")),

        (cb_reset_all, F.data.endswith("~reset_all")),
        (cb_empty, F.data.endswith("~empty")),
    ):
        router.callback_query.register(handler, filter, ModeratorFilter())

    return router
