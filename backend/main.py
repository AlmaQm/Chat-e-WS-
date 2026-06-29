import json
import random
import string
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from pydantic import BaseModel

from ai_client import get_ai_response
from room_manager import RoomManager

load_dotenv()

SECRET_KEY = "dev-secret-key-change-in-prod"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = RoomManager()


class AuthRequest(BaseModel):
    username: str


def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/auth/token")
def get_token(body: AuthRequest):
    if not body.username.strip():
        raise HTTPException(status_code=400, detail="username required")
    return {"token": create_token(body.username.strip())}


@app.post("/rooms")
def create_room():
    room_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return {"room_id": room_id}


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    ws: WebSocket,
    room_id: str,
    token: str = Query(...),
):
    try:
        username = decode_token(token)
    except HTTPException:
        await ws.accept()
        await ws.close(code=1008, reason="Invalid token")
        return

    await manager.join(room_id, ws)
    await manager.broadcast(room_id, {"type": "system", "text": f"{username} se ha unido"}, exclude=ws)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
                text = data.get("text", "").strip()
            except (json.JSONDecodeError, AttributeError):
                continue

            if not text:
                continue

            await manager.broadcast(
                room_id,
                {"type": "message", "user": username, "text": text},
            )

            manager.add_message(room_id, "user", f"{username}: {text}")

            history = manager.get_history(room_id)
            ai_text = await get_ai_response(history)

            manager.add_message(room_id, "assistant", ai_text)
            await manager.broadcast(room_id, {"type": "ai_response", "text": ai_text})

    except WebSocketDisconnect:
        manager.leave(room_id, ws)
        await manager.broadcast(room_id, {"type": "system", "text": f"{username} ha salido"})
