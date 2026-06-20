from contextlib import asynccontextmanager

import aiosqlite

from .schema import User


class Service:
    def __init__(
        self,
        db_path: str = "db.sqlite3",
        tablename: str = "user",
    ):
        self.db_path = db_path
        self._tablename = tablename

    @asynccontextmanager
    async def _session_maker(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db

    async def init_db(self):
        async with self._session_maker() as db:
            await db.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._tablename} (
                    id INTEGER PRIMARY KEY,
                    fullname TEXT NOT NULL,
                    is_active INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            await db.commit()

    async def add(self, user_id: int, fullname: str, is_active: bool = False) -> bool:
        async with self._session_maker() as db:
            cursor = await db.execute(
                f"INSERT INTO {self._tablename} (id, fullname, is_active) VALUES (?, ?, ?)",
                (user_id, fullname, int(is_active)),
            )
            await db.commit()
            return bool(cursor.lastrowid)

    async def _update(self, id: int, data: dict):
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
    
    async def set_is_active(self, user_id: int, value: bool):
        resp = await self._update(user_id, {"is_active": int(value)})
        return bool(resp)
    
    async def get(self, id: int):
        async with self._session_maker() as db:
            async with db.execute(
                f"SELECT * FROM {self._tablename} WHERE id = ?", (id,)
            ) as cursor:
                row = await cursor.fetchone()
                return User(**dict(row)) if row else None
    
    async def get_slice(self, page: int, cap: int = 10, is_active: bool | None = None) -> list[User]:
        query = f"SELECT * FROM {self._tablename}"
        if is_active is not None:
            query +=  f" WHERE is_active = {int(is_active)}"
        query += " ORDER BY created_at DESC LIMIT ?  OFFSET ?"
        offset = 0 if page <= 0 else page * cap
        async with self._session_maker() as db:
            async with db.execute(query, (cap, offset)) as cursor:
                rows = await cursor.fetchall()
                return [User(**dict(r)) for r in rows]

    async def count(self, is_active: bool | None = None) -> int:
        query = f"SELECT COUNT(*) FROM {self._tablename}"
        if is_active is not None:
            query +=  f" WHERE is_active = {int(is_active)};"
        async with self._session_maker() as db:
            async with db.execute(query) as cursor:
                row = await cursor.fetchone()
                return row[0]