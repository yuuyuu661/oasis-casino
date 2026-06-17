BOARD_W = 3
BOARD_H = 4

# black = 下側 / white = 上側
# y=0 が上、y=3 が下

MOVE_RULES = {
    "lion": [
        (-1, -1), (0, -1), (1, -1),
        (-1,  0),          (1,  0),
        (-1,  1), (0,  1), (1,  1),
    ],
    "giraffe": [
        (0, -1), (-1, 0), (1, 0), (0, 1),
    ],
    "elephant": [
        (-1, -1), (1, -1), (-1, 1), (1, 1),
    ],
    "chick": [
        (0, -1),  # ownerごとに反転
    ],
    "chicken": [
        (-1, -1), (0, -1), (1, -1),
        (-1,  0),          (1,  0),
                  (0,  1),
    ],
}


def create_piece(piece_type, owner):
    return {
        "type": piece_type,
        "owner": owner
    }


def create_initial_board():
    return [
        [
            create_piece("giraffe", "white"),
            create_piece("lion", "white"),
            create_piece("elephant", "white"),
        ],
        [
            None,
            create_piece("chick", "white"),
            None,
        ],
        [
            None,
            create_piece("chick", "black"),
            None,
        ],
        [
            create_piece("elephant", "black"),
            create_piece("lion", "black"),
            create_piece("giraffe", "black"),
        ],
    ]


def in_board(x, y):
    return 0 <= x < BOARD_W and 0 <= y < BOARD_H


def enemy(owner):
    return "white" if owner == "black" else "black"


def normalize_captured(piece_type):
    # ニワトリを取ったらヒヨコに戻る
    if piece_type == "chicken":
        return "chick"
    return piece_type


def get_moves_for_piece(piece_type, owner):
    moves = MOVE_RULES[piece_type]

    # redは上方向、blueは下方向
    if owner == "black":
        return moves

    return [(dx, -dy) for dx, dy in moves]


def can_move(board, from_x, from_y, to_x, to_y, owner):
    if not in_board(from_x, from_y):
        return False

    if not in_board(to_x, to_y):
        return False

    piece = board[from_y][from_x]

    if not piece:
        return False

    if piece["owner"] != owner:
        return False

    target = board[to_y][to_x]

    if target and target["owner"] == owner:
        return False

    dx = to_x - from_x
    dy = to_y - from_y

    valid_moves = get_moves_for_piece(
        piece["type"],
        owner
    )

    return (dx, dy) in valid_moves


def should_promote(piece_type, owner, to_y):

    if piece_type != "chick":
        return False

    if owner == "black" and to_y == 0:
        return True

    if owner == "white" and to_y == BOARD_H - 1:
        return True

    return False


def move_piece(state, from_x, from_y, to_x, to_y, owner):
    board = state["board"]

    if state["turn"] != owner:
        return {
            "ok": False,
            "error": "not_your_turn"
        }

    if not can_move(board, from_x, from_y, to_x, to_y, owner):
        return {
            "ok": False,
            "error": "invalid_move"
        }

    piece = board[from_y][from_x]
    target = board[to_y][to_x]

    winner = None

    # ライオンを取ったら勝ち
    if target:
        captured_type = normalize_captured(target["type"])

        state["captured"][owner].append(captured_type)

        if target["type"] == "lion":
            winner = owner

    board[from_y][from_x] = None

    new_type = piece["type"]

    if should_promote(piece["type"], owner, to_y):
        new_type = "chicken"

    board[to_y][to_x] = {
        "type": new_type,
        "owner": owner
    }

    # =========================
    # 前回トライ勝利
    # =========================

    prev_try = state.get("try_winner")

    if prev_try and prev_try != owner:
        winner = prev_try

    # =========================
    # 今回トライ予約
    # =========================

    state["try_winner"] = None

    if new_type == "lion":

        if owner == "black" and to_y == 0:
            state["try_winner"] = "black"

        elif owner == "white" and to_y == BOARD_H - 1:
            state["try_winner"] = "white"

    state["winner"] = winner

    if not winner:
        state["turn"] = enemy(owner)

    return {
        "ok": True,
        "state": state,
        "winner": winner
    }


def can_drop(state, piece_type, x, y, owner):
    board = state["board"]

    if not in_board(x, y):
        return False

    if board[y][x] is not None:
        return False

    if piece_type not in state["captured"][owner]:
        return False

    # ヒヨコは最奥段に打てない
    if piece_type == "chick":
        if owner == "black" and y == 0:
            return False

        if owner == "white" and y == BOARD_H - 1:
            return False

    return True


def drop_piece(state, piece_type, x, y, owner):
    if state["turn"] != owner:
        return {
            "ok": False,
            "error": "not_your_turn"
        }

    if not can_drop(state, piece_type, x, y, owner):
        return {
            "ok": False,
            "error": "invalid_drop"
        }

    state["captured"][owner].remove(piece_type)

    state["board"][y][x] = {
        "type": piece_type,
        "owner": owner
    }

    state["turn"] = enemy(owner)

    return {
        "ok": True,
        "state": state,
    }


def create_initial_state():
    return {
        "board": create_initial_board(),
        "turn": "black",
        "captured": {
            "black": [],
            "white": []
        },
        "winner": None,
        "try_winner": None
    }
