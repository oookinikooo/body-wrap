import calendar
from collections import defaultdict
from datetime import date, datetime

from aiogram.types import InlineKeyboardButton as Button
from aiogram.types import InlineKeyboardMarkup
from src.services.booking import Session
from src.utils.tools import month_alias, month_alias_dec, weekday_alias


class Message:

    @staticmethod
    def pick_hour(d: date):
        return (
            f"{d.day} {month_alias_dec(d.month)} {weekday_alias(d.weekday())}\n\n"
            "Для записи нажмите на нужное время, свободные окошки "
            "выделены зеленым"
        )


class Keyboard:

    @staticmethod
    def menu(appointment_count: int, free_slots: dict[date, int]):
        months = []
        for d in sorted(free_slots):
            months.append(
                [
                    Button(
                        text=f"Записаться на {month_alias(d.month).lower()} ({free_slots[d]})",
                        callback_data=f"{d}~explore_month",
                    )
                ]
            )
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    Button(
                        text=f"Мои записи ({appointment_count})",
                        callback_data="~my_appointment",
                    )
                ],
                *months,
            ]
        )

    @staticmethod
    def month(current_date: date, sessions: list[Session] = []):
        def highlight(day: int):
            return day if day != date.today().day else f"[{day}]"

        now = datetime.now()
        today_month = current_date.year == now.year and current_date.month == now.month

        slots_count = defaultdict(int)
        for s in sessions:
            if s.time.hour == 0:
                continue
            if s.date == now.date() and s.time < now.time():
                continue
            slots_count[s.date.day] += 1

        rows = []
        for week in calendar.monthcalendar(current_date.year, current_date.month):
            row = []
            for day in week:
                if day == 0:
                    text = " "
                elif today_month and day < now.day:
                    text = "x"
                elif slots_count[day] == 0:
                    text = f"{day}"
                else:
                    text = None

                if text:
                    row.append(Button(text=text, callback_data="~empty"))
                    continue

                explore_date = current_date.replace(day=day)
                row.append(
                    Button(
                        text=f"{highlight(day) if today_month else day}",
                        style="success",
                        callback_data=f"{explore_date}~explore_day",
                    ),
                )
            rows.append(row)

        weekdays_header = []
        for number in range(0, 7):
            text = f"{weekday_alias(number)}"
            if today_month and number == now.weekday():
                text = f"[{weekday_alias(number)}]"

            weekdays_header.append(Button(text=text, callback_data="~empty"))

        return InlineKeyboardMarkup(
            inline_keyboard=[
                [Button(text=month_alias(current_date.month), callback_data="~empty")],
                weekdays_header,
                *rows,
                [Button(text="Назад", callback_data="~user_menu")],
            ]
        )

    @staticmethod
    def day(current_date: date, sessions: list[Session]):
        now = datetime.now()

        free_slots = defaultdict(bool)
        ids = defaultdict(int)
        for s in sessions:
            if not s.user.id:
                free_slots[s.time.hour] = True
            ids[s.time.hour] = s.id

        rows = []
        row = []
        for s in sorted(sessions, key=lambda x: x.time):
            hour = s.time.hour
            if now.date() == current_date and hour <= now.hour:
                continue

            row.append(
                Button(
                    text=f"{hour}:00",
                    style="success" if free_slots[hour] else None,
                    callback_data=f"{ids[hour]}~make_appointment" if free_slots[hour] else "~empty",
                ),
            )

            if len(row) == 4:
                rows.append(row)
                row = []
        else:
            if row:
                rows.append(row)
        return InlineKeyboardMarkup(inline_keyboard=[
            *rows,
            [Button(text="Назад", callback_data=f'{current_date}~explore_month')]
        ])

    @staticmethod
    def appointments(sessions: list[Session]):
        rows = []
        for s in sessions:
            text = f"{s.date.day} {month_alias_dec(s.date.month)} " \
                   f"{weekday_alias(s.date.weekday())} {s.time.hour}:00"
            rows.append(
                [
                    Button(
                        text=text.lower(),
                        callback_data=f"{s.id}~~delete_my_appointment",
                    )
                ]
            )

        return InlineKeyboardMarkup(
            inline_keyboard=[*rows, [Button(text="Назад", callback_data="~user_menu")]]
        )

    @staticmethod
    def confirm_cancel_appointment(session: Session):
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    Button(
                        text="Да, отменить запись",
                        style="danger",
                        callback_data=f"{session.id}~1~delete_my_appointment",
                    )
                ],
                [Button(text="Назад", callback_data="~my_appointment")],
            ]
        )
