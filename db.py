import os
import asyncpg

from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()


class Database:

    def __init__(self):
        self.pool = None
        self.dsn = os.getenv("DATABASE_URL")

    async def connect(self):

        if self.pool is None:

            self.pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=1,
                max_size=5
            )

    async def init_db(self):

        await self.connect()

        await self.execute("""
        CREATE TABLE IF NOT EXISTS casino_sessions (
            session_token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            expires_at TIMESTAMP NOT NULL,

            is_active BOOLEAN NOT NULL DEFAULT TRUE
        )
        """)

    # =========================
    # session作成
    # =========================

    async def create_casino_session(
        self,
        session_token,
        user_id,
        guild_id
    ):

        expires_at = (
            datetime.utcnow()
            + timedelta(minutes=30)
        )

        await self.execute("""
        INSERT INTO casino_sessions (
            session_token,
            user_id,
            guild_id,
            expires_at
        )
        VALUES (
            $1,
            $2,
            $3,
            $4
        )
        """,
        session_token,
        user_id,
        guild_id,
        expires_at)

    # =========================
    # session取得
    # =========================

    async def get_casino_session(
        self,
        session_token
    ):

        return await self.fetchrow("""
        SELECT *
        FROM casino_sessions
        WHERE session_token=$1
        AND is_active=TRUE
        AND expires_at > NOW()
        """,
        session_token)

    # =========================
    # 期限切れ削除
    # =========================

    async def delete_expired_sessions(self):

        await self.execute("""
        DELETE FROM casino_sessions
        WHERE expires_at <= NOW()
        """)

    # =========================
    # helper
    # =========================

    async def execute(self, query, *args):

        async with self.pool.acquire() as conn:
            return await conn.execute(
                query,
                *args
            )

    async def fetch(self, query, *args):

        async with self.pool.acquire() as conn:
            return await conn.fetch(
                query,
                *args
            )

    async def fetchrow(self, query, *args):

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                query,
                *args
            )