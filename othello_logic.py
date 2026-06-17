# app/othello_logic.py

SIZE = 8


def create_initial_board():

    board = [[None for _ in range(SIZE)] for _ in range(SIZE)]

    board[3][3] = "white"
    board[4][4] = "white"

    board[3][4] = "black"
    board[4][3] = "black"

    return board


def get_enemy(color):
    return "white" if color == "black" else "black"


def can_place(board, x, y, color):

    if board[y][x] is not None:
        return False

    enemy = get_enemy(color)

    directions = [
        (-1,-1),(0,-1),(1,-1),
        (-1,0),        (1,0),
        (-1,1),(0,1),(1,1)
    ]

    for dx, dy in directions:

        nx = x + dx
        ny = y + dy

        found_enemy = False

        while 0 <= nx < SIZE and 0 <= ny < SIZE:

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

    enemy = get_enemy(color)

    directions = [
        (-1,-1),(0,-1),(1,-1),
        (-1,0),        (1,0),
        (-1,1),(0,1),(1,1)
    ]

    for dx, dy in directions:

        nx = x + dx
        ny = y + dy

        targets = []

        while 0 <= nx < SIZE and 0 <= ny < SIZE:

            value = board[ny][nx]

            if value == enemy:

                targets.append((nx, ny))

            elif value == color:

                if targets:

                    for tx, ty in targets:
                        board[ty][tx] = color

                break

            else:
                break

            nx += dx
            ny += dy


def has_valid_move(board, color):

    for y in range(SIZE):
        for x in range(SIZE):

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
