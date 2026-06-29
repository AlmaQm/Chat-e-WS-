import json
from fastapi import WebSocket


class RoomManager:
    def __init__(self):
        self.rooms: dict[str, set[WebSocket]] = {}
        self.history: dict[str, list[dict]] = {}

    async def join(self, room_id: str, ws: WebSocket):
        await ws.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            self.history[room_id] = []
        self.rooms[room_id].add(ws)

    def leave(self, room_id: str, ws: WebSocket):
        if room_id in self.rooms:
            self.rooms[room_id].discard(ws)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                del self.history[room_id]

    def add_message(self, room_id: str, role: str, content: str):
        if room_id in self.history:
            self.history[room_id].append({"role": role, "content": content})

    def get_history(self, room_id: str) -> list[dict]:
        return self.history.get(room_id, [])

    async def broadcast(self, room_id: str, payload: dict | str, exclude: WebSocket = None):
        if room_id not in self.rooms:
            return
        message = payload if isinstance(payload, str) else json.dumps(payload)
        dead: set[WebSocket] = set()
        for ws in list(self.rooms[room_id]):
            if ws is not exclude:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.add(ws)
        for ws in dead:
            self.rooms[room_id].discard(ws)
