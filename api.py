from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import Database

app = FastAPI()

db = Database()

# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# =========================
# 起動時
# =========================

@app.on_event("startup")
async def startup():

    print("DB接続")

    await db.connect()

    print("DB初期化")

    await db.init_db()

# =========================
# ヘルスチェック
# =========================

@app.get("/")
async def root():

    return {
        "status": "ok"
    }

# =========================
# 自分情報取得
# =========================

@app.get("/api/casino/me")
async def casino_me(
    session: str
):

    row = await db.get_casino_session(
        session
    )

    if not row:

        return {
            "ok": False,
            "error": "invalid_session"
        }

    return {

        "ok": True,

        "user_id":
            row["user_id"],

        # 今は仮
        "user_name":
            f"User-{row['user_id']}",

        # 今は仮
        "balance":
            0

    }