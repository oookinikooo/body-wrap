import calendar
from collections import defaultdict
from datetime import date, datetime

from aiogram.types import InlineKeyboardButton as Button
from aiogram.types import InlineKeyboardMarkup
from src.services.booking import Session
from src.utils.tools import month_alias, weekday_alias, month_alias_dec


class Message:
    @staticmethod
    def menu():
        return (
            "<b>Расписание</b> - записи по неделям и месяцам\n\n"
            "<b>Изменить расписание</b> - добавление нового месяца и изменение "
            "рабочих дней / часов по каждому из месяцев\n"
        )

    @staticmethod
    def edit_time(date: date):
        return (
            f"Изменение рабочего времени <b>{date.day} "
            f"{month_alias_dec(date.month)} {weekday_alias(date.weekday())}</b>\n\n"
            "Нажми на время - оно станет рабочим и будет подсвечено зеленым\n\n"
            "Стоит пометка 👩🏼 - есть запись, если нажать на время с пометкой, "
            "запись будет отменена, а клиенту придет оповещение об отмене"
        )


class Keyboard:
    @staticmethod
    def menu():
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [Button(text="Расписание", callback_data="~schedule_months")],
                [Button(text="Изменить расписание", callback_data="~edit_schedule")],
                [Button(text="Удалить все", style="danger", callback_data="~reset_all")],
            ]
        )

    @staticmethod
    def edit_or_add_months(dates: list[date]):
        rows = []
        row = []
        for d in dates:
            row.append(Button(text=month_alias(d.month), callback_data=f"{d}~edit_month"))
            if len(row) >= 2:
                rows.append(row)
                row = []
        else:
            if row:
                rows.append(row)

        return InlineKeyboardMarkup(inline_keyboard=[
            *rows,
            [Button(text="➕ Добавить новый месяц", callback_data="~add_new_month")],
            [Button(text="Назад", callback_data="~menu")]
        ])

    @staticmethod
    def edit_month(current_date: date, sessions: list[Session] = []):
        def highlight(day: int):
            return day if day != date.today().day else f"[{day}]"

        now = datetime.now()
        today_month = current_date.year == now.year and current_date.month == now.month

        open_slots_count = defaultdict(int)
        for s in sessions:
            if s.time.hour == 0:
                continue
            if now.date() == s.date and s.time < now.time():
                continue
            open_slots_count[s.date.day] += 1

        rows = []
        for week in calendar.monthcalendar(current_date.year, current_date.month):
            row = []
            for day in week:
                if day == 0:
                    text = " "
                elif today_month and day < now.day:
                    text = "x"
                else:
                    text = None

                if text:
                    row.append(Button(text=text, callback_data="~empty"))
                    continue

                edit_date = current_date.replace(day=day)
                row.append(
                    Button(
                        text=f"{highlight(day) if today_month else day}",
                        style="success" if open_slots_count[day] > 0 else "primary",
                        callback_data=f"{edit_date}~edit_day",
                    )
                )
            rows.append(row)

        week_alias = []
        for i in range(0, 7):
            week_day = weekday_alias(i)
            if today_month and i == now.weekday():
                week_day = f"[{week_day}]"

            week_alias.append(Button(text=week_day, callback_data="~empty"))

        return InlineKeyboardMarkup(
            inline_keyboard=[
                [Button(text=month_alias(current_date.month), callback_data="~empty")],
                week_alias,
                *rows,
                [Button(text="Назад", callback_data="~edit_schedule")]
            ]
        )

    @staticmethod
    def edit_day(current_date: date, sessions: list[Session]):
        now = datetime.now()

        ids = defaultdict(int)
        busy_slots = defaultdict(bool)
        actived_hours = defaultdict(bool)
        for s in sessions:
            ids[s.time.hour] = s.id
            actived_hours[s.time.hour] = True
            if s.user.id:
                busy_slots[s.time.hour] = True

        rows = []
        row = []
        for hour in list(range(9, 22)):
            if now.date() == current_date and hour <= now.hour:
                continue

            row.append(
                Button(
                    text=f"{hour}:00 {'👩🏼' if busy_slots[hour] else ''}",
                    style="success" if actived_hours[hour] else None,
                    callback_data=f"{current_date}~{hour}~{ids[hour]}~edit_time",
                )
            )

            if len(row) == 4:
                rows.append(row)
                row = []
        else:
            if row:
                rows.append(row)
        return InlineKeyboardMarkup(inline_keyboard=[
            *rows,
            [Button(text="Назад", callback_data=f'{current_date}~edit_month')]
        ])

    @staticmethod
    def schedule_months(dates: list[date]):
        rows = []
        row = []
        for d in dates:
            row.append(Button(text=month_alias(d.month), callback_data=f'{d}~0~my_schedule'))
            if len(row) >= 2:
                rows.append(row)
                row = []
        else:
            if row:
                rows.append(row)

        return InlineKeyboardMarkup(inline_keyboard=[
            *rows,
            [Button(text="Назад", callback_data="~menu")],
        ])

    @staticmethod
    def week_slider(current_date: date, page: int, total_page: int):
        slider = []
        if page > 0:
            slider.append(
                Button(
                    text="«", callback_data=f"{current_date}~{page-1}~my_schedule"
                )
            )
        slider.append(Button(text='Назад', callback_data="~schedule_months"))
        if page + 1 < total_page:
            slider.append(
                Button(
                    text="»", callback_data=f"{current_date}~{page+1}~my_schedule"
                )
            )
        return InlineKeyboardMarkup(inline_keyboard=[slider])

    @staticmethod
    def reset_db():
        return InlineKeyboardMarkup(inline_keyboard=[
            [Button(text='Да, очистить', style='danger', callback_data='1~reset_all')],
            [Button(text='Назад', callback_data='~menu')],
        ])
