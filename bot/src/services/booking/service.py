from contextlib import asynccontextmanager
from datetime import date, time

import aiosqlite

from .schemas import Session, SessionAdd, User


class Service:

    def __init__(
        self,
        db_path: str = "db.sqlite3",
        tablename: str = "booking",
    ):
        self.db_path = db_path
        self._tablename = tablename
        self._hide_tablename = "deactivated"

    @asynccontextmanager
    async def _session_maker(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db

    async def init_db(self):
        table_names = await self._select_name_of_tables()
        for t in (self._tablename, self._hide_tablename):
            if t in table_names:
                return

        async with self._session_maker() as db:
            await db.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._tablename} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    time TIME NOT NULL,
                    user_id INTEGER,
                    fullname TEXT,
                    reservation_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    async def slot_already_allocated(self, session: SessionAdd) -> bool:
        async with self._session_maker() as db:
            cursor = await db.execute(
                f"SELECT 1 FROM {self._tablename} "
                f'WHERE date == "{session.date}" AND time == "{session.time}"'
            )
            row = await cursor.fetchone()
            return bool(row)

    async def add(self, session: SessionAdd) -> bool:
        async with self._session_maker() as db:
            cursor = await db.execute(
                f"INSERT INTO {self._tablename} (date, time) VALUES (?, ?)",
                (str(session.date), str(session.time)),
            )
            await db.commit()
            return bool(cursor.lastrowid)

    async def get(self, id: int) -> Session | None:
        async with self._session_maker() as db:
            async with db.execute(
                f"SELECT * FROM {self._tablename} WHERE id = ?", (id,)
            ) as cursor:
                row = await cursor.fetchone()
                return Session(**dict(row)) if row else None

    async def update(self, id: int, data: dict):
        if not data:
            return None

        fields = []
        values = []
        for key, value in data.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(id)
        async with self._session_maker() as db:
            async with db.execute(
                f"UPDATE {self._tablename} SET {','.join(fields)} WHERE id = ?",
                tuple(values),
            ) as cursor:
                await db.commit()
                return cursor.rowcount

    async def delete(self, id: int) -> bool:
        async with self._session_maker() as db:
            cursor = await db.execute(
                f"DELETE FROM {self._tablename} WHERE id = ?", (id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_active_month(self) -> list[date]:
        today = date.today()
        async with self._session_maker() as db:
            async with db.execute(
                f'SELECT * FROM {self._tablename} WHERE time = "00:00:00" AND date >= "{today.replace(day=1)}"'
            ) as cursor:
                rows = await cursor.fetchall()
                return sorted([Session(**dict(r)).date for r in rows])

    async def open_new_month(self) -> date:
        dates = await self.get_active_month()
        if not dates:
            new_date = date.today().replace(day=1)
        else:
            last_date = dates[-1]
            if last_date.month == 12:
                new_date = date(last_date.year + 1, 1, 1)
            else:
                new_date = last_date.replace(month=last_date.month + 1)

        _ = await self.add(SessionAdd(date=new_date, time=time()))
        return new_date

    async def get_month_by_date(self, date: date) -> list[Session]:
        async with self._session_maker() as db:
            async with db.execute(
                f"SELECT * FROM {self._tablename} WHERE date like ?",
                (f"{date.year}-{date.month:02d}-%",),
            ) as cursor:
                rows = await cursor.fetchall()
                return [Session(**dict(r)) for r in rows]

    async def get_by_day(self, date: date) -> list[Session]:
        async with self._session_maker() as db:
            async with db.execute(
                f'SELECT * FROM {self._tablename} WHERE date = ? AND time <> "00:00:00"', (str(date),)
            ) as cursor:
                rows = await cursor.fetchall()
                return [Session(**dict(r)) for r in rows]

    async def clear_all(self):
        async with self._session_maker() as db:
            async with db.execute(f"DELETE FROM {self._tablename}") as cursor:
                await db.commit()
                return cursor.lastrowid

    async def make_appointment(self, session_id: int, user: User):
        resp = await self.update(
            session_id,
            {
                "user_id": user.id,
                "fullname": user.fullname,
                "reservation_at": user.reservation_at,
            },
        )
        return bool(resp)

    async def reset_appointment(self, session_id: int):
        resp = await self.update(
            session_id,
            {
                "user_id": None,
                "fullname": None,
                "reservation_at": None,
            },
        )
        return bool(resp)

    async def user_appointments(self, user_id: int):
        query = f'''
            SELECT * FROM {self._tablename}
            WHERE
                user_id = ?
                AND datetime(date || ' ' || time) >= datetime('now', 'localtime')
            ORDER BY datetime(date || ' ' || time);
        '''
        async with self._session_maker() as db:
            async with db.execute(query, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [Session(**dict(r)) for r in rows]

    async def get_month_slots_count(self):
        query = f'''
            SELECT
                strftime('%Y-%m', date) as month,
                COUNT(*) as total_slots
            FROM {self._tablename}
            WHERE
                user_id IS NULL
                AND time <> '00:00:00'
                AND datetime(date || ' ' || time) >= datetime('now', 'localtime')
            GROUP BY strftime('%Y-%m', date)
            ORDER BY month;
        '''
        async with self._session_maker() as db:
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                resp = dict()
                for r in rows:
                    data = dict(r)
                    resp[date.fromisoformat(f"{data['month']}-01")] = data["total_slots"]
                return resp

    async def _select_name_of_tables(self):
        async with self._session_maker() as db:
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r)["name"] for r in rows]

    async def _change_table(self, old_name: str, new_name: str):
        async with self._session_maker() as db:
            async with self._session_maker() as db:
                async with db.execute(
                    f"ALTER TABLE {old_name} RENAME TO {new_name}"
                ) as cursor:
                    await db.commit()
                    return cursor.lastrowid

    async def hide(self):
        return await self._change_table(self._tablename, self._hide_tablename)

    async def unhide(self):
        return await self._change_table(self._hide_tablename, self._tablename)

    async def is_hiden(self):
        tables = await self._select_name_of_tables()
        if self._hide_tablename in tables:
            return True
        return False

    async def get_expired_sessions(self):
        query =  f'''
            SELECT * FROM {self._tablename}
            WHERE
                datetime(date || ' ' || time) < datetime('now', 'localtime')
        '''
        async with self._session_maker() as db:
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [Session(**dict(r)) for r in rows]
