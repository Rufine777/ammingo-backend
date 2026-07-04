from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

import secrets
import string
import qrcode
from io import BytesIO
import base64
import os
import uuid
import shutil

from app.db.db import get_db
from app.middlewares.verify_token import get_current_user
from app.db.models import Game, Bingo, User, BingoTiles

from datetime import datetime, timedelta, timezone
from app.models.game import (
    CreateGameRequest,
    JoinGameRequest,
    StartGameRequest,
    CreateGameResponse,
    JoinGameResponse,
    LobbyResponse,
    StartGameResponse,
    GameDetailResponse,
    BingoBoardResponse,
    TileResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    TileSubmit,
)
import random

router = APIRouter()
UPLOAD_DIR = "uploads/"


def generate_game_code():
    characters = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(characters) for _ in range(6))


def create_unique_code(db: Session):
    while True:
        code = generate_game_code()
        existing = db.query(Game).filter(Game.code == code).first()
        if not existing:
            return code


def generate_qr_base64(code: str):
    BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    join_url = f"{BASE_URL}/api/games/join/{code}"

    qr = qrcode.make(join_url)

    buffer = BytesIO()
    qr.save(buffer, format="PNG")

    return base64.b64encode(buffer.getvalue()).decode()


@router.post("/games", response_model=CreateGameResponse)
def create_game(data: CreateGameRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):

    code = create_unique_code(db)
    qr_img = generate_qr_base64(code)
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(minutes=data.duration)

    new_game = Game(
        host_id=current_user.id,
        description=data.description,
        location=data.location,
        start_time=start_time,
        end_time=end_time,
        code=code,
        qr_img=qr_img,
    )

    db.add(new_game)
    db.commit()
    db.refresh(new_game)

    return {
        "game_id": new_game.id,
        "join_code": new_game.code,
        "qr_img": f"data:image/png;base64,{new_game.qr_img}",
    }


@router.post("/games/join/{code}", response_model=JoinGameResponse)
def join_game(code: str, data: JoinGameRequest, 
      db: Session = Depends(get_db), 
      current_user = Depends(get_current_user)
    ):

    game = db.query(Game).filter(Game.code == code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    existing = db.query(Bingo).filter_by(game_id=game.id, user_id=current_user.id).first()

    if existing:
        return {
            "message": "User already joined",
            "game_id": game.id,
            "username": current_user.username
        }

    if game.board_size is not None:
        raise HTTPException(status_code=400, detail="Game already started")

    board = Bingo(game_id=game.id, user_id=current_user.id)

    db.add(board)
    db.commit()

    return {
        "message": "Joined successfully",
        "game_id": game.id,
        "username": current_user.username,
    }


@router.get("/games/{code}/lobby", response_model=LobbyResponse)
def get_lobby(code: str, db: Session = Depends(get_db)):

    game = db.query(Game).filter(Game.code == code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    players = (
        db.query(User.name)
        .join(Bingo, Bingo.user_id == User.id)
        .filter(Bingo.game_id == game.id)
        .all()
    )

    player_names = [p.name for p in players]

    return {
        "player_count": len(player_names),
        "players": player_names,
        "available_board_sizes": [3, 4, 5],
    }


@router.post("/games/{code}/start", response_model=StartGameResponse)
def start_game(code: str, data: StartGameRequest, 
               db: Session = Depends(get_db), 
               current_user: User = Depends(get_current_user)
    ):

    game = db.query(Game).filter(Game.code == code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if current_user.id != game.host_id:
        raise HTTPException(status_code=403, detail="Only host can start the game")

    if game.board_size is not None:
        raise HTTPException(status_code=400, detail="Game already started")

    game.board_size = data.size

    participants = db.query(Bingo).filter(Bingo.game_id == game.id).all()

    for participant in participants:
        create_bingo_matrix(db, game, participant.user_id)

    db.commit()

    return {"message": "Game started", "board_size": data.size}


def create_bingo_matrix(db: Session, game: Game, user_id: int):

    board = db.query(Bingo).filter_by(game_id=game.id, user_id=user_id).first()

    if not board:
        raise HTTPException(status_code=404, detail="Board not found for user")

    size = game.board_size
    total_tiles = size * size

    other_players = (
        db.query(User)
        .join(Bingo, Bingo.user_id == User.id)
        .filter(Bingo.game_id == game.id)
        .filter(User.id != user_id)
        .all()
    )

    if len(other_players) < total_tiles:
        raise HTTPException(
            status_code=400, detail=f"Not enough players to fill a {size}x{size} board"
        )

    random.shuffle(other_players)
    selected_players = other_players[:total_tiles]

    for i, player in enumerate(selected_players):
        new_tile = BingoTiles(
            row=i // size,
            col=i % size,
            bingo_char=player.name.strip()[0].upper(),
            bingo_id=board.id,
        )
        db.add(new_tile)


@router.get("/games/{code}", response_model=GameDetailResponse)
def get_game_details(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    game = db.query(Game).filter(Game.code == code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return GameDetailResponse(
        game_id=game.id,
        host_name=current_user.name,
        description=game.description,
        location=game.location,
        start_time=game.start_time,
        end_time=game.end_time,
        code=game.code,
        board_size=game.board_size,
        qr_img=f"data:image/png;base64,{game.qr_img}" if game.qr_img else None,
    )


@router.get("/games/{code}/board/", response_model=BingoBoardResponse)
def get_user_board(code: str,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    game = db.query(Game).filter(Game.code == code).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    board = db.query(Bingo).filter_by(game_id=game.id, user_id=current_user.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    tiles = (
        db.query(BingoTiles)
        .filter(BingoTiles.bingo_id == board.id)
        .order_by(BingoTiles.row, BingoTiles.col)
        .all()
    )

    return BingoBoardResponse(
        bingo_id=board.id,
        username=current_user.username,
        game_id=board.game_id,
        points=board.points,
        tiles=[
            TileResponse(
                id=tile.id, row=tile.row, col=tile.col, bingo_char=tile.bingo_char
            )
            for tile in tiles
        ],
    )

@router.get("/games/{code}/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(code: str, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.code == code).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    results = (
        db.query(User.code, User.name, User.username, Bingo.points)
        .join(Bingo, Bingo.user_id == User.id)
        .filter(Bingo.game_id == game.id)
        .order_by(Bingo.points.desc())
        .all()
    )

    leaderboard = [
        LeaderboardEntry(code=r.code,name=r.name, username=r.username, points=r.points)
        for r in results
    ]

    return LeaderboardResponse(leaderboard=leaderboard)

@router.post("/games/tile-submit", response_model=TileSubmit)
def tile_submit(
    bingo_id: int,
    row: int,
    col: int,
    friend_name: str,
    friend_code: str,
    fact: str,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    friend = (
        db.query(User)
        .filter(User.name == friend_name, User.code == friend_code)
        .first()
    )
    if not friend:
        raise HTTPException(status_code=404, detail="Friend not found or code mismatch")
    bingo = db.query(Bingo).filter(Bingo.id == bingo_id).first()
    if not bingo:
        raise HTTPException(status_code=404, detail="Bingo board not found")

    tile = (
        db.query(BingoTiles)
        .filter(
            BingoTiles.bingo_id == bingo_id,
            BingoTiles.row == row,
            BingoTiles.col == col,
        )
        .first()
    )
    if not tile:
        raise HTTPException(status_code=404, detail="Tile not found")
    if tile.image_url:
        raise HTTPException(status_code=400, detail="Tile already submitted")

    ext = os.path.splitext(image.filename)[-1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    tile.image_url = filepath
    tile.random_fact = fact
    db.commit()
    db.refresh(tile)

    n = bingo.game.board_size
    submitted = {
        (i.row, i.col)
        for i in db.query(BingoTiles).filter(BingoTiles.bingo_id == bingo_id).all()
        if i.image_url
    }

    points = 0

    if all((row, c) in submitted for c in range(n)):
        points += 500

    if all((r, col) in submitted for r in range(n)):
        points += 500

    if row == col and all((i, i) in submitted for i in range(n)):
        points += 500
    if row + col == n - 1 and all((i, n - 1 - i) in submitted for i in range(n)):
        points += 500

    points = points if points > 0 else 100
    bingo.points += points
    db.commit()

    return tile
