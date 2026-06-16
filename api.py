import os
import secrets
import asyncio
import socketio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import Database


# =========================
# 設定
# =========================

RATE_TABLE = {
    2000: "超低レート",
    5000: "低レート",
    10000: "中レート",
    30000: "高レート",
    50000: "超高レート",
    100000: "絶頂レート",
    300000: "超絶頂レート",
}

GAME_MAX_PLAYERS = {
    "othello": 2,
    "dobutsu": 2,
    "poker": 6,
    "daifugo": 4,
    "chinchiro": 6,
}


# =========================
# FastAPI
# =========================

app = FastAPI()
# =========================
# Socket.IO
# =========================

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*"
)

socket_app = socketio.ASGIApp(
    sio,
    other_asgi_app=app
)

OTHELLO_GAMES = {}
CONNECTED_USERS = {}

WIN_MAP = {
    "gu": "choki",
    "choki": "pa",
    "pa": "gu"
}

db = Database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# 起動処理
# =========================

@app.on_event("startup")
async def startup():

    print("DB接続")
    await db.connect()

    print("DB初期化")
    await db.init_db()

    async def cleanup_loop():

        while True:

            try:
                await db.delete_expired_sessions()

            except Exception as e:
                print("SESSION CLEANUP ERROR:", e)

            await asyncio.sleep(60)

    asyncio.create_task(cleanup_loop())


# =========================
# ヘルスチェック
# =========================

@app.get("/")
async def root():

    return {
        "status": "ok",
        "service": "oasis-casino-api"
    }


# =========================
# Request Models
# =========================

class CreateRoomRequest(BaseModel):

    session: str
    game: str
    rate: int
    room_name: str | None = None
    password: str | None = None


class JoinRoomRequest(BaseModel):

    room_id: str
    session: str
    password: str | None = None


class LeaveRoomRequest(BaseModel):

    room_id: str
    session: str


# =========================
# 共通
# =========================

async def get_session_or_403(
    session_token: str
):

    session_data = await db.get_casino_session(
        session_token
    )

    if not session_data:

        raise HTTPException(
            status_code=403,
            detail="Invalid session"
        )

    return session_data


def safe_room_name(
    name: str | None,
    host_name: str
):

    if not name:
        return f"{host_name}のロビー"

    name = name.strip()

    if not name:
        return f"{host_name}のロビー"

    return name[:30]


def make_guest_name(
    user_id: str
):

    return f"User-{user_id[-4:]}"


# =========================
# 自分情報
# =========================

@app.get("/api/casino/me")
async def casino_me(
    session: str
):

    session_data = await get_session_or_403(
        session
    )

    user_id = session_data["user_id"]
    guild_id = session_data["guild_id"]

    user_name = make_guest_name(
        user_id
    )

    # VPS残高連携前なので仮
    balance = 999999999

    return {
        "ok": True,
        "user_id": user_id,
        "guild_id": guild_id,
        "user_name": user_name,
        "balance": balance
    }


# =========================
# ルーム一覧
# =========================

@app.get("/api/casino/rooms")
async def casino_rooms(
    game: str
):

    rows = await db.get_rooms(
        game
    )

    return {
        "ok": True,
        "rooms": [
            {
                "room_id": r["room_id"],
                "host_name": r["host_name"],
                "room_name": r["room_name"],
                "has_password": r["has_password"],
                "current_players": r["current_players"],
                "max_players": r["max_players"],
                "status": r["status"],
                "rate_name": r["rate_name"],
                "rate_amount": r["rate_amount"],
            }
            for r in rows
        ]
    }


# =========================
# ルーム作成
# =========================

@app.post("/api/casino/create-room")
async def create_room(
    body: CreateRoomRequest
):

    session_data = await get_session_or_403(
        body.session
    )

    if body.game not in GAME_MAX_PLAYERS:

        return {
            "ok": False,
            "error": "invalid_game"
        }

    if body.rate not in RATE_TABLE:

        return {
            "ok": False,
            "error": "invalid_rate"
        }

    user_id = session_data["user_id"]
    guild_id = session_data["guild_id"]

    host_name = make_guest_name(
        user_id
    )

    room_id = secrets.token_hex(3).upper()

    room_name = safe_room_name(
        body.room_name,
        host_name
    )

    password = (
        body.password.strip()
        if body.password and body.password.strip()
        else None
    )

    max_players = GAME_MAX_PLAYERS.get(
        body.game,
        2
    )

    await db.create_room(
        room_id=room_id,
        game_type=body.game,
        host_user_id=user_id,
        host_name=host_name,
        guild_id=guild_id,
        room_name=room_name,
        room_password=password,
        has_password=password is not None,
        rate_name=RATE_TABLE[body.rate],
        rate_amount=body.rate
    )

    await db.join_room(
        room_id=room_id,
        user_id=user_id,
        user_name=host_name
    )

    await db.update_room_players(
        room_id,
        1
    )
    # =========================
    # オセロ初期化
    # =========================

    if body.game == "othello":

        OTHELLO_GAMES[room_id] = {
            "board": create_initial_board(),
            "turn": "black",

            "players": {
                "black": None,
                "white": None
            },

            "users": [
                user_id
            ],

            "janken": {
                "choices": {},
                "done": False
            },

            "started": False,
            "finished": False
        }

    return {
        "ok": True,
        "room_id": room_id
    }




# =========================
# ルーム参加
# =========================

@app.post("/api/casino/join-room")
async def join_room(
    body: JoinRoomRequest
):

    session_data = await get_session_or_403(
        body.session
    )

    user_id = session_data["user_id"]

    room = await db.get_room(
        body.room_id
    )

    if not room:

        return {
            "ok": False,
            "error": "room_not_found"
        }

    if room["status"] == "finished":

        return {
            "ok": False,
            "error": "room_finished"
        }

    if room["room_password"]:

        if body.password != room["room_password"]:

            return {
                "ok": False,
                "error": "wrong_password"
            }

    players = await db.get_room_players(
        body.room_id
    )

    already = any(
        p["user_id"] == user_id
        for p in players
    )

    if already:

        return {
            "ok": True
        }

    if len(players) >= room["max_players"]:

        return {
            "ok": False,
            "error": "room_full"
        }

    user_name = make_guest_name(
        user_id
    )

    await db.join_room(
        body.room_id,
        user_id,
        user_name
    )
    # =========================
    # オセロ参加者追加
    # =========================

    game = OTHELLO_GAMES.get(
        body.room_id
    )

    if game:

        if user_id not in game["users"]:

            game["users"].append(
                user_id
            )

    new_count = await db.get_room_player_count(
        body.room_id
    )

    new_status = (
        "playing"
        if new_count >= room["max_players"]
        else "waiting"
    )

    await db.update_room_players(
        body.room_id,
        new_count
    )

    await db.update_room_status(
        body.room_id,
        new_status
    )

    return {
        "ok": True
    }


# =========================
# ルーム退出
# =========================

@app.post("/api/casino/leave-room")
async def leave_room(
    body: LeaveRoomRequest
):

    session_data = await get_session_or_403(
        body.session
    )

    user_id = session_data["user_id"]

    await db.leave_room(
        body.room_id,
        user_id
    )

    count = await db.get_room_player_count(
        body.room_id
    )

    if count <= 0:

        await db.delete_room(
            body.room_id
        )

        return {
            "ok": True
        }

    room = await db.get_room(
        body.room_id
    )

    if room:

        new_status = (
            "playing"
            if count >= room["max_players"]
            else "waiting"
        )

        await db.update_room_players(
            body.room_id,
            count
        )

        await db.update_room_status(
            body.room_id,
            new_status
        )

    return {
        "ok": True
    }


# =========================
# ルーム情報
# =========================

@app.get("/api/casino/room-info")
async def room_info(
    room_id: str
):

    room = await db.get_room(
        room_id
    )

    if not room:

        return {
            "ok": False,
            "error": "room_not_found"
        }

    players = await db.get_room_players(
        room_id
    )

    return {
        "ok": True,

        "room": {
            "room_id": room["room_id"],
            "game_type": room["game_type"],
            "status": room["status"],
            "rate_name": room["rate_name"],
            "rate_amount": room["rate_amount"],
        },

        "black_user_id": room["black_user_id"],
        "white_user_id": room["white_user_id"],

        "players": [
            {
                "user_id": p["user_id"],
                "user_name": p["user_name"],
            }
            for p in players
        ]
    }

# =========================
# オセロロジック
# =========================

def create_initial_board():

    board = [[None for _ in range(8)] for _ in range(8)]

    board[3][3] = "white"
    board[4][4] = "white"
    board[3][4] = "black"
    board[4][3] = "black"

    return board


def can_place(board, x, y, color):

    if board[y][x]:
        return False

    enemy = "white" if color == "black" else "black"

    directions = [
        (-1, -1), (0, -1), (1, -1),
        (-1,  0),          (1,  0),
        (-1,  1), (0,  1), (1,  1),
    ]

    for dx, dy in directions:

        nx = x + dx
        ny = y + dy

        found_enemy = False

        while 0 <= nx < 8 and 0 <= ny < 8:

            value = board[ny][nx]

            if value == enemy:
                found_enemy = True

            elif value == color:

                if found_enemy:
                    return True

                break

            else:
                break

            nx += dx
            ny += dy

    return False


def flip_stones(board, x, y, color):

    enemy = "white" if color == "black" else "black"

    directions = [
        (-1, -1), (0, -1), (1, -1),
        (-1,  0),          (1,  0),
        (-1,  1), (0,  1), (1,  1),
    ]

    for dx, dy in directions:

        nx = x + dx
        ny = y + dy

        targets = []

        while 0 <= nx < 8 and 0 <= ny < 8:

            value = board[ny][nx]

            if value == enemy:
                targets.append((nx, ny))

            elif value == color:

                for tx, ty in targets:
                    board[ty][tx] = color

                break

            else:
                break

            nx += dx
            ny += dy


def has_valid_move(board, color):

    for y in range(8):
        for x in range(8):

            if can_place(board, x, y, color):
                return True

    return False


def count_stones(board):

    black = 0
    white = 0

    for row in board:
        for cell in row:

            if cell == "black":
                black += 1

            elif cell == "white":
                white += 1

    return {
        "black": black,
        "white": white
    }


# =========================
# Socket接続
# =========================

@sio.event
async def connect(sid, environ, auth):

    room_id = None
    session = None
    game_type = None

    if auth:

        room_id = auth.get("room_id")
        session = auth.get("session")
        game_type = auth.get("game")

    print("SOCKET CONNECT", sid, room_id, game_type)

    if session:

        session_data = await db.get_casino_session(
            session
        )

        if session_data:

            CONNECTED_USERS[sid] = {
                "room_id": room_id,
                "user_id": session_data["user_id"],
                "game": game_type
            }

    if room_id and game_type == "othello":

        await sio.enter_room(
            sid,
            f"othello:{room_id}"
        )

        game = OTHELLO_GAMES.get(room_id)

        if game:

            await sio.emit(
                "othello:update",
                {
                    "board": game["board"],
                    "current_turn": game["turn"]
                },
                to=sid
            )

            if (
                len(game["users"]) >= 2
                and not game["janken"]["done"]
            ):

                await sio.emit(
                    "janken:start",
                    {},
                    room=f"othello:{room_id}"
                )


@sio.event
async def disconnect(sid):

    print("SOCKET DISCONNECT", sid)

    CONNECTED_USERS.pop(
        sid,
        None
    )


# =========================
# join_room
# =========================

@sio.on("join_room")
async def socket_join_room(sid, data):

    room_id = data.get("room_id")
    game_type = data.get("game")

    if not room_id:
        return

    if game_type == "othello":

        await sio.enter_room(
            sid,
            f"othello:{room_id}"
        )


# =========================
# チャット
# =========================

@sio.event
async def chat_message(sid, data):

    room_id = data.get("room_id")
    user_name = data.get("user_name")
    message = data.get("message")
    game_type = data.get("game")

    if not room_id or not message:
        return

    message = str(message)[:200]

    await sio.emit(
        "chat_message",
        {
            "user_name": user_name or "Unknown",
            "message": message
        },
        room=f"{game_type}:{room_id}"
    )


# =========================
# じゃんけん
# =========================

@sio.event
async def janken_select(sid, data):

    room_id = data.get("room_id")
    hand = data.get("hand")
    game_type = data.get("game", "othello")

    connected = CONNECTED_USERS.get(sid)

    if not connected:
        return

    user_id = connected["user_id"]

    if hand not in ["gu", "choki", "pa"]:
        return

    if game_type != "othello":
        return

    game = OTHELLO_GAMES.get(room_id)

    if not game:
        return

    if user_id not in game["users"]:
        return

    if game["janken"]["done"]:
        return

    game["janken"]["choices"][user_id] = hand

    if len(game["janken"]["choices"]) < 2:

        await sio.emit(
            "janken:wait",
            {},
            to=sid
        )

        return

    user1 = game["users"][0]
    user2 = game["users"][1]

    hand1 = game["janken"]["choices"][user1]
    hand2 = game["janken"]["choices"][user2]

    if hand1 == hand2:

        game["janken"]["choices"] = {}

        await sio.emit(
            "janken:draw",
            {},
            room=f"othello:{room_id}"
        )

        return

    if WIN_MAP[hand1] == hand2:

        winner = user1
        loser = user2

    else:

        winner = user2
        loser = user1

    game["players"]["black"] = winner
    game["players"]["white"] = loser

    game["turn"] = "black"
    game["janken"]["done"] = True
    game["started"] = True

    await db.set_room_colors(
        room_id,
        winner,
        loser
    )

    await sio.emit(
        "janken:result",
        {
            "black_user_id": winner,
            "white_user_id": loser
        },
        room=f"othello:{room_id}"
    )

    await sio.emit(
        "othello:update",
        {
            "board": game["board"],
            "current_turn": game["turn"]
        },
        room=f"othello:{room_id}"
    )


# =========================
# オセロ操作
# =========================

@sio.event
async def othello_move(sid, data):

    room_id = data.get("room_id")
    x = data.get("x")
    y = data.get("y")
    user_id = str(data.get("user_id"))

    game = OTHELLO_GAMES.get(room_id)

    if not game:
        return

    if game.get("finished"):
        return

    board = game["board"]
    current_turn = game["turn"]
    players = game["players"]

    player_color = None

    if players["black"] == user_id:
        player_color = "black"

    elif players["white"] == user_id:
        player_color = "white"

    else:
        return

    if player_color != current_turn:
        return

    if not can_place(
        board,
        x,
        y,
        current_turn
    ):
        return

    board[y][x] = current_turn

    flip_stones(
        board,
        x,
        y,
        current_turn
    )

    next_turn = (
        "white"
        if current_turn == "black"
        else "black"
    )

    if has_valid_move(board, next_turn):

        game["turn"] = next_turn

    elif has_valid_move(board, current_turn):

        game["turn"] = current_turn

    else:

        game["finished"] = True

        counts = count_stones(board)

        black_count = counts["black"]
        white_count = counts["white"]

        if black_count > white_count:
            winner = "black"

        elif white_count > black_count:
            winner = "white"

        else:
            winner = "draw"

        await db.finish_othello_game(
            room_id,
            winner
        )

        await db.update_room_status(
            room_id,
            "finished"
        )

        await sio.emit(
            "othello:update",
            {
                "board": board,
                "current_turn": game["turn"]
            },
            room=f"othello:{room_id}"
        )

        await sio.emit(
            "othello:finish",
            {
                "winner": winner,
                "black": black_count,
                "white": white_count
            },
            room=f"othello:{room_id}"
        )

        return

    await db.update_othello_game(
        room_id,
        board,
        game["turn"]
    )

    await sio.emit(
        "othello:update",
        {
            "board": board,
            "current_turn": game["turn"]
        },
        room=f"othello:{room_id}"
    )
