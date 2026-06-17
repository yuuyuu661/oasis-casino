import os
import asyncpg

from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()


class Database:

    def __init__(self):

        self.pool = None

        self.dsn = os.getenv(
            "DATABASE_URL"
        )

    # =========================
    # 接続
    # =========================

    async def connect(self):

        if self.pool is None:

            self.pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=1,
                max_size=10
            )

            async with self.pool.acquire() as conn:

                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM users"
                )

                print(
                    f"USERS TABLE OK : {count}"
                )

    # =========================
    # 初期化
    # =========================

    async def init_db(self):

        await self.connect()

        # =========================
        # セッション
        # =========================

        await self.execute("""
        CREATE TABLE IF NOT EXISTS casino_sessions (

            session_token TEXT PRIMARY KEY,

            user_id TEXT NOT NULL,

            guild_id TEXT NOT NULL,

            created_at TIMESTAMP NOT NULL
                DEFAULT NOW(),

            expires_at TIMESTAMP NOT NULL,

            is_active BOOLEAN NOT NULL
                DEFAULT TRUE

        )
        """)

        # =========================
        # ルーム
        # =========================

        await self.execute("""
        CREATE TABLE IF NOT EXISTS casino_rooms (

            room_id TEXT PRIMARY KEY,

            game_type TEXT NOT NULL,

            host_user_id TEXT NOT NULL,

            host_name TEXT NOT NULL,

            guild_id TEXT NOT NULL,

            room_name TEXT NOT NULL,

            room_password TEXT,

            has_password BOOLEAN NOT NULL
                DEFAULT FALSE,

            status TEXT NOT NULL
                DEFAULT 'waiting',

            current_players INTEGER NOT NULL
                DEFAULT 1,

            max_players INTEGER NOT NULL
                DEFAULT 2,

            rate_name TEXT NOT NULL,

            rate_amount BIGINT NOT NULL,

            black_user_id TEXT,

            white_user_id TEXT,

            created_at TIMESTAMP NOT NULL
                DEFAULT NOW()

        )
        """)

        # =========================
        # 参加者
        # =========================

        await self.execute("""
        CREATE TABLE IF NOT EXISTS casino_room_players (

            room_id TEXT NOT NULL,

            user_id TEXT NOT NULL,

            user_name TEXT NOT NULL,

            joined_at TIMESTAMP NOT NULL
                DEFAULT NOW(),

            PRIMARY KEY (
                room_id,
                user_id
            )

        )
        """)

        # =========================
        # オセロ
        # =========================

        await self.execute("""
        CREATE TABLE IF NOT EXISTS othello_games (

            room_id TEXT PRIMARY KEY,

            board JSONB NOT NULL,

            current_turn TEXT NOT NULL,

            started BOOLEAN NOT NULL
                DEFAULT FALSE,

            finished BOOLEAN NOT NULL
                DEFAULT FALSE,

            winner TEXT,

            created_at TIMESTAMP NOT NULL
                DEFAULT NOW()

        )
        """)

    # ==================================================
    # SESSION
    # ==================================================

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

    async def delete_expired_sessions(self):

        await self.execute("""
        DELETE
        FROM casino_sessions
        WHERE expires_at <= NOW()
        """)

    # ==================================================
    # ROOM
    # ==================================================

    async def create_room(
        self,
        room_id,
        game_type,
        host_user_id,
        host_name,
        guild_id,
        room_name,
        room_password,
        has_password,
        rate_name,
        rate_amount
    ):

        await self.execute("""
        INSERT INTO casino_rooms (

            room_id,
            game_type,

            host_user_id,
            host_name,

            guild_id,

            room_name,

            room_password,
            has_password,

            rate_name,
            rate_amount

        )
        VALUES (

            $1,
            $2,

            $3,
            $4,

            $5,

            $6,

            $7,
            $8,

            $9,
            $10

        )
        """,
        room_id,
        game_type,
        host_user_id,
        host_name,
        guild_id,
        room_name,
        room_password,
        has_password,
        rate_name,
        rate_amount)

    async def get_room(
        self,
        room_id
    ):

        return await self.fetchrow("""
        SELECT *
        FROM casino_rooms
        WHERE room_id=$1
        """,
        room_id)

    async def get_rooms(
        self,
        game_type
    ):

        return await self.fetch("""
        SELECT *
        FROM casino_rooms
        WHERE game_type=$1
        ORDER BY created_at DESC
        """,
        game_type)

    async def update_room_status(
        self,
        room_id,
        status
    ):

        await self.execute("""
        UPDATE casino_rooms
        SET status=$2
        WHERE room_id=$1
        """,
        room_id,
        status)

    async def update_room_players(
        self,
        room_id,
        current_players
    ):

        await self.execute("""
        UPDATE casino_rooms
        SET current_players=$2
        WHERE room_id=$1
        """,
        room_id,
        current_players)

    async def set_room_colors(
        self,
        room_id,
        black_user_id,
        white_user_id
    ):

        await self.execute("""
        UPDATE casino_rooms
        SET

            black_user_id=$2,
            white_user_id=$3

        WHERE room_id=$1
        """,
        room_id,
        black_user_id,
        white_user_id)

    async def delete_room(
        self,
        room_id
    ):

        await self.execute("""
        DELETE
        FROM casino_rooms
        WHERE room_id=$1
        """,
        room_id)

    # ==================================================
    # ROOM PLAYERS
    # ==================================================

    async def join_room(
        self,
        room_id,
        user_id,
        user_name
    ):

        await self.execute("""
        INSERT INTO casino_room_players (

            room_id,
            user_id,
            user_name

        )
        VALUES (
            $1,
            $2,
            $3
        )
        ON CONFLICT DO NOTHING
        """,
        room_id,
        user_id,
        user_name)

    async def leave_room(
        self,
        room_id,
        user_id
    ):

        await self.execute("""
        DELETE
        FROM casino_room_players
        WHERE room_id=$1
        AND user_id=$2
        """,
        room_id,
        user_id)

    async def get_room_players(
        self,
        room_id
    ):

        return await self.fetch("""
        SELECT *
        FROM casino_room_players
        WHERE room_id=$1
        ORDER BY joined_at
        """,
        room_id)

    async def get_room_player_count(
        self,
        room_id
    ):

        row = await self.fetchrow("""
        SELECT COUNT(*) AS count
        FROM casino_room_players
        WHERE room_id=$1
        """,
        room_id)

        return row["count"]

    # ==================================================
    # OTHELLO
    # ==================================================

    async def create_othello_game(
        self,
        room_id,
        board,
        current_turn
    ):

        await self.execute("""
        INSERT INTO othello_games (

            room_id,
            board,
            current_turn

        )
        VALUES (
            $1,
            $2,
            $3
        )
        ON CONFLICT (room_id)
        DO NOTHING
        """,
        room_id,
        board,
        current_turn)

    async def get_othello_game(
        self,
        room_id
    ):

        return await self.fetchrow("""
        SELECT *
        FROM othello_games
        WHERE room_id=$1
        """,
        room_id)

    async def update_othello_game(
        self,
        room_id,
        board,
        current_turn
    ):

        await self.execute("""
        UPDATE othello_games

        SET

            board=$2,
            current_turn=$3

        WHERE room_id=$1
        """,
        room_id,
        board,
        current_turn)

    async def finish_othello_game(
        self,
        room_id,
        winner
    ):

        await self.execute("""
        UPDATE othello_games

        SET

            finished=TRUE,
            winner=$2

        WHERE room_id=$1
        """,
        room_id,
        winner)

    # ==================================================
    # HELPER
    # ==================================================

    async def execute(
        self,
        query,
        *args
    ):

        async with self.pool.acquire() as conn:

            return await conn.execute(
                query,
                *args
            )

    async def fetch(
        self,
        query,
        *args
    ):

        async with self.pool.acquire() as conn:

            return await conn.fetch(
                query,
                *args
            )

    async def fetchrow(
        self,
        query,
        *args
    ):

        async with self.pool.acquire() as conn:

            return await conn.fetchrow(
                query,
                *args
            )
