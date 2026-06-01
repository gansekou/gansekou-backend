import uuid
from typing import Dict, Set, Any

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()

        key = str(user_id)

        if key not in self.active_connections:
            self.active_connections[key] = set()

        self.active_connections[key].add(websocket)

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket):
        key = str(user_id)

        if key in self.active_connections:
            self.active_connections[key].discard(websocket)

            if not self.active_connections[key]:
                del self.active_connections[key]

    async def send_to_user(self, user_id: uuid.UUID, data: dict[str, Any]):
        key = str(user_id)

        if key not in self.active_connections:
            return

        disconnected = []

        for websocket in self.active_connections[key]:
            try:
                await websocket.send_json(data)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.active_connections[key].discard(websocket)

    async def broadcast(self, data: dict[str, Any]):
        for user_id in list(self.active_connections.keys()):
            for websocket in list(self.active_connections[user_id]):
                try:
                    await websocket.send_json(data)
                except Exception:
                    self.active_connections[user_id].discard(websocket)

    def is_user_online(self, user_id: uuid.UUID) -> bool:
        return str(user_id) in self.active_connections


websocket_manager = WebSocketManager()