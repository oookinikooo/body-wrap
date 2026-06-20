from datetime import date

from src.services.booking import Session
from src.services.user import User
from src.utils.tools import month_alias_dec, weekday_alias


class UserMessage:
    def info(self, user: User) -> str:
        if user.is_active:
            status = " ✅ Может записаться на посещение"
        else:
            status = " ❌ Не может записаться на посещение"
        return (
            f'#{user.id} - <b><a href="tg://user?id={user.id}">{user.fullname}</a></b>\n\n'
            f"{status}\n\n"
            f"Дата регистрации: {user.created_at:%d.%m.%Y %H:%M:%S}"
        )


class Message:
    user = UserMessage()
    @staticmethod
    def menu():
        return (
            "<b>Расписание</b> - записи по неделям и месяцам\n\n"
            "<b>Изменить расписание</b> - добавление нового месяца и изменение "
            "рабочих дней / часов по каждому из месяцев\n"
            "<b>Пользователи</b> - просмотр и действия над пользователями"
        )

    @staticmethod
    def edit_time(date: date):
        return (
            f"<b>{date.day} {month_alias_dec(date.month)} "
            f"{weekday_alias(date.weekday())}</b> "
            "изменение рабочего времени\n\n"
            "Нажми на время - оно станет рабочим и будет подсвечено зеленым\n\n"
            "Стоит пометка 👩🏼 - есть запись, если нажать на время с пометкой, "
            "запись будет отменена, а клиенту придет оповещение об отмене"
        )

    @staticmethod
    def session_rejected(session: Session):
        return (
            "❗️ Внимание!\n"
            f"Сеанс {session.date:%d.%m.%Y} {session.time:%H:%M} был отменен модератором"
        )
